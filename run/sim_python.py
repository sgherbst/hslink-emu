from numpy import genfromtxt
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import fftconvolve, lfilter
from scipy.interpolate import interp1d
from scipy.stats import describe
from math import floor
import os.path
import sys
import logging
from random import random

from msemu.ctle import RxDynamics
from msemu.pwl import Waveform
from msemu.cmd import get_parser
from msemu.ila import IlaData
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
    def __init__(self, RX_SETTING, TX_SETTING, KP_LF, KI_LF, DCO_CODE_INIT, JITTER_SCALE_RX, JITTER_SCALE_TX):
        self.RX_SETTING = RX_SETTING
        self.TX_SETTING = TX_SETTING
        self.KP_LF = KP_LF
        self.KI_LF = KI_LF
        self.DCO_CODE_INIT = DCO_CODE_INIT
        self.JITTER_SCALE_RX = JITTER_SCALE_RX
        self.JITTER_SCALE_TX = JITTER_SCALE_TX

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
    JITTER_SCALE_RX = 700,
    JITTER_SCALE_TX = 700
)

steady_state = SimConfig(
    RX_SETTING = 4,
    TX_SETTING = 4,
    KP_LF = 256,
    KI_LF = 1,
    DCO_CODE_INIT = 8192,
    JITTER_SCALE_RX = 700,
    JITTER_SCALE_TX = 700
)


# def get_ideal(rx_dyn, tx, rx_setting):
#
#     # interpolate input to impulse response timebase
#     count = int(floor(tx.t[-1]/imp.dt))+1
#     assert (count-1)*imp.dt <= tx.t[-1]
#     assert count*imp.dt > tx.t[-1]
#     in_t = np.arange(count)*imp.dt
#     in_v = interp1d(tx.t, tx.v, kind='zero')(in_t)
#
#     # simulate system response
#     out_v = fftconvolve(in_v, imp.v)[:len(in_t)] * imp.dt
#
#     # return waveforms
#     return IdealResult(
#         in_ = Waveform(t=in_t, v=in_v),
#         out = Waveform(t=in_t, v=out_v)
#     )
#
# def report_error(data, ideal):
#     # compose list of times where the emulation output will be checked
#     t_emu = np.concatenate((data.rxn.t, data.rxp.t))
#     v_emu = np.concatenate((data.rxn.v, data.rxp.v))
#     test_idx = t_emu <= ideal.out.t[-1]
#
#     # compute error at those times
#     v_sim_interp = interp1d(ideal.out.t, ideal.out.v)(t_emu[test_idx])
#     err = v_emu[test_idx] - v_sim_interp
#
#     # compute percentage error
#     v_out_abs_max = np.max(np.abs(ideal.out.v))
#     plus_err = np.max(err)/v_out_abs_max
#     minus_err = np.min(err) / v_out_abs_max
#
#     print('error: {:+3f} / {:+3f} %'.format(plus_err*1e2, minus_err*1e2))
#     print('')
#     print('error statistics: ')
#     print(describe(err))
#
# def plot_waveforms(data, ideal, fig_dir, plot_prefix, fmts=['png', 'pdf', 'eps']):
#     #plt.step(ideal.in_.t, ideal.in_.v, '-k', where='post', label='in')
#     plt.plot(ideal.out.t*1e9, ideal.out.v, '-g', label='Ideal', linewidth=1)
#     plt.plot(np.concatenate((data.rxp.t, data.rxn.t))*1e9,
#              np.concatenate((data.rxp.v, data.rxn.v)),
#              'bo', label='Emulation', markersize=2)
#     plt.ylim(-0.66, 0.65)
#     plt.xlim(10.3, 16.9)
#     plt.legend(loc='lower left')
#     plt.xlabel('Time (ns)')
#     plt.ylabel('Value')
#     plt.title('Transient Accuracy')
#
#     plot_name = os.path.join(fig_dir, plot_prefix+'_emu_vs_ideal_comparison')
#     for fmt in fmts:
#         plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')
#
#     plt.show()
#

def tx_period():
    freq = 8e9
    return 1/freq

def rx_period(code, fmin=7.5e9, fmax=8.5e9, n=14):
    freq = fmin + ((fmax-fmin)/((1<<n)-1)) * code
    #freq = 8e9
    return 1/freq

# TX evaluation function
def eval_tx(t, cfg, t_tx, v_tx):
    # find index, and make sure it's in the right place
    idx = np.searchsorted(t_tx, t) - 1
    assert t-t_tx[idx] > 0
    assert t-t_tx[idx+1] <= 0

    out = 0
    first_tap = False
    while 0 < (t-t_tx[idx]) < cfg.tmax:

        # edges
        tr = t - t_tx[idx]
        tf = t - t_tx[idx + 1]

        # compute pulse response
        pulse = cfg.step(tr)
        if tf > 0:
            pulse -= cfg.step(tf)
        else:
            assert not first_tap
            first_tap = True

        # compute product
        prod = v_tx[idx] * pulse

        # update output
        out += prod

        # go back in time one UI
        idx -= 1

    return out

def run_sim(cfg, num_ui=16000):
    # generate TX bits
    ntx = 2*num_ui
    tx_bits = np.where(np.random.rand(ntx) > 0.5, np.ones(ntx), -np.ones(ntx))

    # generate TX values
    v_tx = lfilter(cfg.tx_taps, [1], tx_bits)

    # generate TX times
    t_tx = np.zeros(len(v_tx), dtype=float)
    for k in range(1,len(t_tx)):
        t_tx[k] = t_tx[k-1] + tx_period() #+cfg.tx_jitter.get()

    # Registers
    in_hist = Reg(init=[])

    a = Reg()
    b = Reg()
    t = Reg()
    data = Reg()

    cfg.DCO_CODE_INIT = 6700
    out = Reg(init=cfg.DCO_CODE_INIT)
    prev = Reg()

    #time = 35e-12
    time = 0
    time_disp = 0

    dco_codes = []
    v_ctle = []
    v_dfe = []

    for k in range(num_ui):
        # positive clock edge
        # most actions happen here

        # increment time to the RX clock edge
        time_inc_p = rx_period(out.value)/2 #+cfg.rx_jitter.get()
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
        dco_codes.append(out.value)
        v_ctle.append(ctle_out_p)
        v_dfe.append(dfe_out_p)
        ##############################

        # negative clock edge clock edge

        # increment time to the RX clock edge
        time_inc_n = rx_period(out.value)/2 #+cfg.rx_jitter.get()
        time += time_inc_n

        # Comparator
        ctle_out_n = eval_tx(time, cfg, t_tx, v_tx)
        dfe_out_n = ctle_out_n
        for coeff, val in zip(cfg.dfe_taps, [data.value]+in_hist.value):
            dfe_out_n -= coeff*(val-0.5)*2
        t.next = 1 if dfe_out_n > 0 else 0

        # Update register
        t.update()

        if (time-time_disp) > 100e-9:
            print('{:0.3f}'.format(time*1e9))
            time_disp = time

    #plt.plot(errs)
    #plt.show()
    #print(np.mean(errs))

    plt.plot(dco_codes)
    plt.show()

    n_skip = round(0.5*num_ui)
    #n_skip = 0
    plt.hist(v_dfe[n_skip:], 100, normed=1, facecolor='blue', alpha=1, label='DFE Output')
    plt.hist(v_ctle[n_skip:], 100, normed=1, facecolor='green', alpha=0.5, label='CTLE Output')
    plt.show()

    # plt.hist(v_dfe_n[n_skip:], 50, normed=1, facecolor='blue', alpha=1, label='DFE Output')
    # plt.hist(v_ctle_n[n_skip:], 50, normed=1, facecolor='green', alpha=0.5, label='CTLE Output')
    # plt.show()

    # plt.legend(loc='upper center')
    #
    # plt.xlabel('Voltage')
    # plt.ylabel('Probability Density')
    # plt.title('RX Signal Histograms')

def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    sim_config = steady_state
    #sim_config = large_step
    sim_config.set_args(args)

    run_sim(sim_config)

    # # get combined impulse response of channel and RX
    #
    #
    # run_sim(sim_config=steady_state)
    #
    # # create the RxDynamics object
    # rx_dyn = RxDynamics()
    #
    # if args.use_ila:
    #     fmt_dict_file = os.path.join(args.build_dir, 'fmt_dict.json')
    #     ila_dir_name = os.path.join(args.data_dir, 'ila', 'large_step')
    #     ila_data = IlaData(ila_dir_name=ila_dir_name, fmt_dict_file=fmt_dict_file)
    #     data = Data(tx=ila_data.tx.filter_in,
    #                 rxp=ila_data.rxp.filter_out,
    #                 rxn=ila_data.rxn.filter_out)
    #
    #     plot_prefix = 'ila'
    # else:
    #     data = get_sim_data(args.data_dir)
    #     plot_prefix = 'sim'
    #
    # ideal = get_ideal(rx_dyn=rx_dyn, tx=data.tx, rx_setting=args.rx_setting)
    #
    # report_error(data=data, ideal=ideal)
    #
    # plot_waveforms(data=data, ideal=ideal, fig_dir=args.fig_dir, plot_prefix=plot_prefix)
    
if __name__=='__main__':
    main()
