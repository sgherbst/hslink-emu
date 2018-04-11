from numpy import genfromtxt
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import fftconvolve
from scipy.interpolate import interp1d
from scipy.stats import describe
from math import floor
import os.path
import sys
import argparse

from msemu.ctle import RxCTLE
from msemu.pwl import Waveform
from msemu.fixed import PointFormat

class SimResult:
    def __init__(self, tx, rxp, rxn, imp, in_, out):
        self.tx = tx
        self.rxp = rxp
        self.rxn = rxn
        self.imp = imp
        self.in_ = in_
        self.out = out

class IlaData:
    def __init__(self, time_tx, sig_tx, time_rx_p, sig_rx_p, time_rx_n, sig_rx_n,
                 time_point=47, sig_tx_point=14, sig_rx_point=17):
        # define formats
        self.time_fmt = PointFormat(time_point)
        self.sig_tx_fmt = PointFormat(sig_tx_point)
        self.sig_rx_fmt = PointFormat(sig_rx_point)

        t_tx = np.array(self.time_fmt.floatval(time_tx))
        v_tx = np.array(self.sig_tx_fmt.floatval(sig_tx[1:]+[sig_tx[-1]]))
        self.tx = Waveform(t=t_tx, v=v_tx)

        t_rx_p = np.array(self.time_fmt.floatval(time_rx_p))
        v_rx_p = np.array(self.sig_rx_fmt.floatval(sig_rx_p))
        self.rxp = Waveform(t=t_rx_p, v=v_rx_p)

        t_rx_n = np.array(self.time_fmt.floatval(time_rx_n))
        v_rx_n = np.array(self.sig_rx_fmt.floatval(sig_rx_n))
        self.rxn = Waveform(t=t_rx_n, v=v_rx_n)

def get_imp_eff(rx_setting):
    # compute the impulse response
    rx_ctle = RxCTLE()
    step = rx_ctle.get_combined_step(rx_setting)
    v_new = np.diff(step.v)/step.dt
    t_new = step.t[:-1]    

    return Waveform(t=t_new, v=v_new)

def read_ila_data(fpga_freq=40e6):
    # read file
    with open('iladata.csv', 'r') as f:
        lines = f.readlines()

    # skip header for now
    lines = lines[1:]

    time_rx_p = []
    time_rx_n = []
    time_tx = []
    sig_rx_p = []
    sig_rx_n = []
    sig_tx = []
    for k, line in enumerate(lines):
        line_split = line.split(',')
        sim_done = int(line_split[-1].strip())
        if sim_done == 1:
            break
        cke_rx_n = int(line_split[6].strip())
        cke_rx_p = int(line_split[7].strip())
        cke_tx = int(line_split[8].strip())
        sig_rx_val = int(line_split[4].strip())
        sig_tx_val = int(line_split[5].strip())
        time_curr = int(line_split[3].strip(), base=16)
        if cke_tx == 1:
            time_tx.append(time_curr)
            sig_tx.append(sig_tx_val)
        if cke_rx_p == 1:
            time_rx_p.append(time_curr)
            sig_rx_p.append(sig_rx_val)
        if cke_rx_n == 1:
            time_rx_n.append(time_curr)
            sig_rx_n.append(sig_rx_val)

    num_fpga_cycles = k

    ila_data = IlaData(time_tx=time_tx, sig_tx=sig_tx,
                       time_rx_p=time_rx_p, sig_rx_p=sig_rx_p,
                        time_rx_n=time_rx_n, sig_rx_n=sig_rx_n)

    real_time = num_fpga_cycles/fpga_freq
    emu_time = max(ila_data.tx.t[-1], ila_data.rxp.t[-1], ila_data.rxn.t[-1])
    print('Number of FPGA cycles: {}'.format(num_fpga_cycles))
    print('Real time: {} (s)'.format(real_time))
    print('Emulated time: {} (us)'.format(1e6*emu_time))
    print('Emulation rate: {} (s/us)'.format(real_time / (1e6*emu_time)))

    return ila_data

def eval(rx_setting):
    # read data and assign to local variables
    ila_data = read_ila_data()

    tx = ila_data.tx
    rxp = ila_data.rxp
    rxn = ila_data.rxn

    # get impulse response of channel
    imp = get_imp_eff(rx_setting)

    # interpolate input to impulse response timebase
    count = int(floor(tx.t[-1]/imp.dt))+1
    assert (count-1)*imp.dt <= tx.t[-1]
    assert count*imp.dt > tx.t[-1]
    in_t = np.arange(count)*imp.dt
    in_v = interp1d(tx.t, tx.v, kind='zero')(in_t)

    # simulate system response
    out_v = fftconvolve(in_v, imp.v)[:len(in_t)] * imp.dt

    # return waveforms
    return SimResult(
        tx = tx,
        rxp = rxp,
        rxn = rxn,
        imp = imp,
        in_ = Waveform(t=in_t, v=in_v),
        out = Waveform(t=in_t, v=out_v)
    )

def measure_error(result):
    t_emu = np.concatenate((result.rxn.t, result.rxp.t))
    v_emu = np.concatenate((result.rxn.v, result.rxp.v))
    test_idx = t_emu <= result.out.t[-1]

    v_sim_interp = interp1d(result.out.t, result.out.v)(t_emu[test_idx])
    err = v_emu[test_idx] - v_sim_interp

    # compute percentage error
    v_out_abs_max = np.max(np.abs(result.out.v))
    print('v_out_abs_max: {}'.format(v_out_abs_max))
    plus_err = np.max(err)/v_out_abs_max
    minus_err = np.min(err) / v_out_abs_max

    print('error: {:+3f} / {:+3f} %'.format(plus_err*1e2, minus_err*1e2))
    print('')
    print('error statistics: ')
    print(describe(err))

    return err

def plot(result):
    plt.step(result.in_.t, result.in_.v, '-k', where='post', label='in')
    plt.plot(result.rxp.t, result.rxp.v, 'bo', label='rxp', markersize=3)
    plt.plot(result.rxn.t, result.rxn.v, 'ro', label='rxn', markersize=3)
    plt.plot(result.out.t, result.out.v, '-g', label='sim')
    plt.ylim(-1.25, 1.25)
    plt.legend(loc='lower right')
    plt.xlabel('time')
    plt.ylabel('value')
    plt.show()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rx_setting', type=int, default=0, help='Setting of the RX CTLE.')
    args = parser.parse_args()

    result = eval(args.rx_setting)

    measure_error(result)
    plot(result)
    
if __name__=='__main__':
    main()
