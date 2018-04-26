import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import lfilter
from scipy.interpolate import interp1d
import os.path
import sys
import logging
from random import random

from msemu.ctle import RxDynamics
from msemu.cmd import get_parser
from msemu.verilog import VerilogPackage
from msemu.tx_ffe import TxFFE
from msemu.dfe import DfeDesigner

# simulation settings

class Reg:
    def __init__(self, init=0):
        self._value = init
        self._next = init
        self._assigned = False

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, x):
        raise Exception('Cannot write value')

    @property
    def next(self):
        raise Exception('Cannot read next')

    @next.setter
    def next(self, x):
        assert not self._assigned
        self._next = x
        self._assigned = True

    def update(self):
        assert self._assigned
        self._value = self._next
        self._assigned = False

class Jitter:
    def __init__(self, lfsr_width, jitter_scale_point, jitter_scale):
        self.jitter_pkpk = (1 << lfsr_width) * jitter_scale * (2 ** (-jitter_scale_point))

    def get(self):
        return (random() - 0.5)*self.jitter_pkpk

class SimConfig:
    def __init__(self, RX_SETTING, TX_SETTING, KP_LF, KI_LF, DCO_CODE_INIT, JITTER_SCALE_RX, JITTER_SCALE_TX, name):
        self.RX_SETTING = RX_SETTING
        self.TX_SETTING = TX_SETTING
        self.KP_LF = KP_LF
        self.KI_LF = KI_LF
        self.DCO_CODE_INIT = DCO_CODE_INIT
        self.JITTER_SCALE_RX = JITTER_SCALE_RX
        self.JITTER_SCALE_TX = JITTER_SCALE_TX
        self.name = name

    def set_args(self, args):
        self.args = args

        # determine meaning of jitter scale in picoseconds

        pack = VerilogPackage.from_file(os.path.join(args.build_dir, 'time_package.sv'))

        # rx jitter
        self.rx_jitter = Jitter(lfsr_width=pack.get('RX_JITTER_LFSR_WIDTH').value,
                                jitter_scale_point=pack.get('RX_JITTER_SCALE_POINT').value,
                                jitter_scale=self.JITTER_SCALE_RX)

        # tx jitter
        self.tx_jitter = Jitter(lfsr_width=pack.get('TX_JITTER_LFSR_WIDTH').value,
                                jitter_scale_point=pack.get('TX_JITTER_SCALE_POINT').value,
                                jitter_scale=self.JITTER_SCALE_TX)

        # store object containing RX dynamics
        self.rx_dyn = RxDynamics(dir_name=self.args.channel_dir)
        self.tx_ffe = TxFFE()
        self.tx_taps = self.tx_ffe.tap_table[self.TX_SETTING]

        self.dfe_des = DfeDesigner(tx_ffe=self.tx_ffe, rx_dyn=self.rx_dyn, ui=125e-12)
        self.dfe_taps = self.dfe_des.get_resp(tx_setting=self.TX_SETTING,
                                              rx_setting=self.RX_SETTING).get_isi(2)

        step_wave = self.rx_dyn.get_step(self.RX_SETTING)
        self.tmax = step_wave.t[-1]
        self.step = interp1d(step_wave.t, step_wave.v)

large_step = SimConfig(
    RX_SETTING = 4,
    TX_SETTING = 4,
    KP_LF = 256,
    KI_LF = 16,
    DCO_CODE_INIT = 1000,
    JITTER_SCALE_RX = 0,  # TODO: change this
    JITTER_SCALE_TX = 0,  # TODO: change this
    name = 'LargeStepPySim'
)

steady_state = SimConfig(
    RX_SETTING = 4,
    TX_SETTING = 4,
    KP_LF = 256,
    KI_LF = 1,
    DCO_CODE_INIT = 8192,
    JITTER_SCALE_RX = 0,  # TODO: change this
    JITTER_SCALE_TX = 0,  # TODO: change this
    name = 'SteadyStatePySim'
)

def tx_period():
    freq = 8e9
    return 1/freq

def rx_period(code, fmin=7.5e9, fmax=8.5e9, n=14):
    freq = fmin + ((fmax-fmin)/((1<<n)-1)) * code
    return 1/freq

# TX evaluation function
def eval_tx(t, cfg, t_tx, v_tx):
    # find the first index, and make sure it's in the right place
    start = np.searchsorted(t_tx, t - cfg.tmax)
    assert t-t_tx[start] <= cfg.tmax
    if start != 0:
        assert t-t_tx[start-1] > cfg.tmax

    # find last index, and make sure it's in the right place
    stop = np.searchsorted(t_tx, t) - 1
    assert t-t_tx[stop] > 0
    assert t-t_tx[stop+1] <= 0

    steps = cfg.step(t-t_tx[start:stop+1])
    out = steps[-1] * v_tx[stop]

    if stop > start:
        out += np.diff(steps).dot(v_tx[start:stop])

    return out

def run_sim(cfg, num_ui=4000, out_dir=None):
    # generate TX bits
    ntx = 2*num_ui
    tx_bits = np.where(np.random.rand(ntx) > 0.5, np.ones(ntx), -np.ones(ntx))

    # generate TX values
    v_tx = lfilter(cfg.tx_taps, [1], tx_bits)

    # generate TX times
    t_tx = np.zeros(len(v_tx), dtype=float)
    for k in range(1,len(t_tx)):
        t_tx[k] = t_tx[k-1] + tx_period() #+ cfg.tx_jitter.get()

    # Registers
    in_hist = Reg(init=[0]*(len(cfg.dfe_taps)-1))

    a = Reg()
    b = Reg()
    t = Reg()
    data = Reg()

    out = Reg(init=cfg.DCO_CODE_INIT)
    prev = Reg()

    time = 0
    time_disp = 0

    time_vals = []
    dco_codes = []
    v_ctle = []
    v_dfe = []

    for k in range(num_ui):
        dco_code = out.value

        # negative clock edge clock edge

        # increment time to the RX clock edge
        time_inc_n = rx_period(dco_code)/2 +cfg.rx_jitter.get()
        time += time_inc_n

        # Comparator
        ctle_out_n = eval_tx(time, cfg, t_tx, v_tx)
        dfe_out_n = ctle_out_n
        assert len(cfg.dfe_taps) == len([data.value]+in_hist.value)
        for coeff, val in zip(cfg.dfe_taps, [data.value]+in_hist.value):
            dfe_out_n -= coeff*(val-0.5)*2
        t.next = 1 if dfe_out_n > 0 else 0

        # Update register
        t.update()

        # positive clock edge
        # most actions happen here

        # increment time to the RX clock edge
        time_inc_p = rx_period(dco_code)/2 +cfg.rx_jitter.get()
        time += time_inc_p

        # DFE
        in_hist.next = [data.value] + in_hist.value[:-1]

        # BBPD
        a.next = data.value
        b.next = t.value
        up = a.value ^ b.value
        dn = data.value ^ b.value

        # Digital LF
        curr = up - dn
        prev.next = curr
        out.next = out.value + curr*(cfg.KI_LF+cfg.KP_LF) - prev.value*(cfg.KP_LF)

        # Comparator
        ctle_out_p = eval_tx(time, cfg, t_tx, v_tx)
        dfe_out_p = ctle_out_p
        assert len(cfg.dfe_taps) == len([data.value] + in_hist.value)
        for coeff, val in zip(cfg.dfe_taps, [data.value]+in_hist.value):
            dfe_out_p -= coeff*(val-0.5)*2
        data.next = 1 if dfe_out_p > 0 else 0

        # update registers
        in_hist.update()
        a.update()
        b.update()
        data.update()
        out.update()
        prev.update()

        ##############################
        # record results
        time_vals.append(time)
        dco_codes.append(out.value)
        v_ctle.append(ctle_out_p)
        v_dfe.append(dfe_out_p)

        if (time-time_disp) > 100e-9:
            print('{:0.3f}'.format(time*1e9))
            time_disp = time
        ##############################

    plt.plot(time_vals, dco_codes)
    plt.xlabel('Time')
    plt.ylabel('DCO Code')
    plt.title(cfg.name)
    plt.show()

    # write to folder
    out_mat = np.column_stack((time_vals, dco_codes, v_ctle, v_dfe))
    np.save(os.path.join(out_dir, cfg.name), out_mat)

def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    steady_state.set_args(args)
    large_step.set_args(args)

    run_sim(cfg=steady_state, num_ui=1<<14, out_dir=args.data_dir)
    run_sim(cfg=large_step, num_ui=1<<14, out_dir=args.data_dir)

if __name__=='__main__':
    main()
