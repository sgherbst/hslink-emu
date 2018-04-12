from numpy import genfromtxt
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import fftconvolve
from scipy.interpolate import interp1d
from scipy.stats import describe
from math import floor
import os.path
import sys
import logging
import json

from msemu.ctle import RxDynamics
from msemu.pwl import Waveform
from msemu.cmd import get_parser
from msemu.fixed import Fixed

class Data:
    def __init__(self, tx, rxp, rxn):
        self.tx = tx
        self.rxp = rxp
        self.rxn = rxn

class IdealResult:
    def __init__(self, in_, out):
        self.in_ = in_
        self.out = out

def parse_ila_header(header, in_fmt, out_fmt, time_fmt):
    # split header into column names
    cols = header.strip().split(',')

    # determine column locations of the signals of interest
    time_curr = cols.index('time_curr[{}:{}]'.format(time_fmt.n-1,0))
    sig_rx = cols.index('sig_rx[{}:{}]'.format(out_fmt.n - 1, 0))
    sig_tx = cols.index('sig_tx[{}:{}]'.format(in_fmt.n - 1, 0))
    cke_rx_p = cols.index('cke_rx_p')
    cke_rx_n = cols.index('cke_rx_n')
    cke_tx = cols.index('cke_tx')
    sim_done = cols.index('sim_done_reg')

    # create dictionary mapping a signal name to an index
    cols = {
        'time_curr': time_curr,
        'sig_rx': sig_rx,
        'sig_tx': sig_tx,
        'cke_rx_n': cke_rx_n,
        'cke_rx_p': cke_rx_p,
        'cke_tx': cke_tx,
        'sim_done': sim_done
    }

    # make sure that all signals of interest were found
    assert all(cols != -1 for cols in cols.values())

    return cols

def get_ila_data(build_dir, data_dir):
    # get data formats
    with open(os.path.join(build_dir, 'fmt_dict.json')) as f:
        fmt_dict = json.loads(f.read())

    in_fmt = Fixed.from_dict(fmt_dict['in_fmt'])
    out_fmt = Fixed.from_dict(fmt_dict['out_fmt'])
    time_fmt = Fixed.from_dict(fmt_dict['time_fmt'])

    # read data file, splitting on commands
    data_file = os.path.join(data_dir, 'iladata.csv')
    with open(data_file, 'r') as f:
        header = f.readline()

    # read the rest of the data
    cols = parse_ila_header(header, in_fmt, out_fmt, time_fmt)
    data = genfromtxt(data_file, delimiter=',', skip_header=1, autostrip=True, dtype=int)

    # determine range of valid data
    valid = data[:, cols['sim_done']] != 1

    # get TX data
    rows_tx = np.logical_and(data[:, cols['cke_tx']], valid) == 1
    # adjust piecewise constant representation
    v_tx = data[rows_tx, cols['sig_tx']]*in_fmt.res
    v_tx = np.concatenate((v_tx[1:], [v_tx[-1]]))
    tx = Waveform(t=data[rows_tx, cols['time_curr']]*time_fmt.res,
                  v=v_tx)

    # get RXP data
    rows_rx_p = np.logical_and(data[:, cols['cke_rx_p']], valid) == 1
    rxp = Waveform(t=data[rows_rx_p, cols['time_curr']]*time_fmt.res,
                   v=data[rows_rx_p, cols['sig_rx']]*out_fmt.res)

    # get RXN data
    rows_rx_n = np.logical_and(data[:, cols['cke_rx_n']], valid) == 1
    rxn = Waveform(t=data[rows_rx_n, cols['time_curr']]*time_fmt.res,
                   v=data[rows_rx_n, cols['sig_rx']]*out_fmt.res)

    return Data(tx=tx, rxp=rxp, rxn=rxn)

def get_sim_data(data_dir):
    # determine file names
    tx_file_name = os.path.join(data_dir, 'tx.txt')
    rxp_file_name = os.path.join(data_dir, 'rxp.txt')
    rxn_file_name = os.path.join(data_dir, 'rxn.txt')

    # read tx data
    data_tx = genfromtxt(tx_file_name, delimiter=',')
    t_tx = data_tx[:, 0]
    v_tx = data_tx[1:, 1]
    v_tx = np.concatenate((v_tx, [v_tx[-1]]))
    tx = Waveform(t=t_tx, v=v_tx)
    
    # read rxp data (positive clock edge sampling)
    data_rxp = genfromtxt(rxp_file_name, delimiter=',')
    rxp = Waveform(t=data_rxp[:, 0], v=data_rxp[:, 1])
    
    # read rxn data (negative clock edge sampling)
    data_rxn = genfromtxt(rxn_file_name, delimiter=',')
    rxn = Waveform(t=data_rxn[:, 0], v=data_rxn[:, 1])

    return Data(tx=tx, rxp=rxp, rxn=rxn)

def get_ideal(rx_dyn, tx, rx_setting):
    # get combined impulse response of channel and RX
    imp = rx_dyn.get_imp(rx_setting)
    
    # interpolate input to impulse response timebase
    count = int(floor(tx.t[-1]/imp.dt))+1
    assert (count-1)*imp.dt <= tx.t[-1]
    assert count*imp.dt > tx.t[-1]
    in_t = np.arange(count)*imp.dt
    in_v = interp1d(tx.t, tx.v, kind='zero')(in_t)

    # simulate system response
    out_v = fftconvolve(in_v, imp.v)[:len(in_t)] * imp.dt

    # return waveforms
    return IdealResult(
        in_ = Waveform(t=in_t, v=in_v),
        out = Waveform(t=in_t, v=out_v)
    )

def report_error(data, ideal):
    # compose list of times where the emulation output will be checked
    t_emu = np.concatenate((data.rxn.t, data.rxp.t))
    v_emu = np.concatenate((data.rxn.v, data.rxp.v))
    test_idx = t_emu <= ideal.out.t[-1]

    # compute error at those times
    v_sim_interp = interp1d(ideal.out.t, ideal.out.v)(t_emu[test_idx])
    err = v_emu[test_idx] - v_sim_interp

    # compute percentage error
    v_out_abs_max = np.max(np.abs(ideal.out.v))
    plus_err = np.max(err)/v_out_abs_max
    minus_err = np.min(err) / v_out_abs_max

    print('error: {:+3f} / {:+3f} %'.format(plus_err*1e2, minus_err*1e2))
    print('')
    print('error statistics: ')
    print(describe(err))

def plot_waveforms(data, ideal, dir_name, plot_prefix):
    plt.step(ideal.in_.t, ideal.in_.v, '-k', where='post', label='in')
    plt.plot(data.rxp.t, data.rxp.v, 'bo', label='rxp', markersize=3)
    plt.plot(data.rxn.t, data.rxn.v, 'ro', label='rxn', markersize=3)
    plt.plot(ideal.out.t, ideal.out.v, '-g', label='sim')
    plt.ylim(-1.25, 1.25)
    plt.legend(loc='lower right')
    plt.xlabel('time')
    plt.ylabel('value')
    plt.savefig(os.path.join(dir_name, plot_prefix+'_transient.pdf'))
    plt.show()

def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    parser.add_argument('--rx_setting', type=int, help='Setting of the RX CTLE.')
    parser.add_argument('--use_ila', action='store_true', help='Use ILA data instead of simulation data.')
    args = parser.parse_args()

    # create the RxDynamics object
    rx_dyn = RxDynamics(dir_name=args.channel_dir)

    if args.use_ila:
        data = get_ila_data(build_dir=args.build_dir, data_dir=args.data_dir)
        plot_prefix = 'ila'
    else:
        data = get_sim_data(args.data_dir)
        plot_prefix = 'sim'

    ideal = get_ideal(rx_dyn=rx_dyn, tx=data.tx, rx_setting=args.rx_setting)

    report_error(data=data, ideal=ideal)

    plot_waveforms(data=data, ideal=ideal, dir_name=args.data_dir, plot_prefix=plot_prefix)
    
if __name__=='__main__':
    main()
