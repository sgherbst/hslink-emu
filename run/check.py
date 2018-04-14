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

from msemu.ctle import RxDynamics
from msemu.pwl import Waveform
from msemu.cmd import get_parser
from msemu.ila import IlaData

class Data:
    def __init__(self, tx, rxp, rxn):
        self.tx = tx
        self.rxp = rxp
        self.rxn = rxn

class IdealResult:
    def __init__(self, in_, out):
        self.in_ = in_
        self.out = out

def get_ila_data(ila_data):
    # get data formats



    tx_file = os.path.join(data_dir, 'ila', 'large_step', 'ila_0_data.csv')
    rx_p_file = os.path.join(data_dir, 'ila', 'large_step', 'ila_1_data.csv')
    rx_n_file = os.path.join(data_dir, 'ila', 'large_step', 'ila_2_data.csv')

    tx = read_ila_tx(tx_file, in_fmt=in_fmt, time_fmt=time_fmt)
    rxp = read_ila_rx_p(rx_p_file, out_fmt=out_fmt, time_fmt=time_fmt)
    rxn = read_ila_rx_n(rx_n_file, out_fmt=out_fmt, time_fmt=time_fmt)

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

def plot_waveforms(data, ideal, fig_dir, plot_prefix, fmts=['png', 'pdf', 'eps']):
    #plt.step(ideal.in_.t, ideal.in_.v, '-k', where='post', label='in')
    plt.plot(np.concatenate((data.rxp.t, data.rxn.t))*1e9,
             np.concatenate((data.rxp.v, data.rxn.v)),
             'bo', label='Emulation', markersize=2)
    plt.plot(ideal.out.t*1e9, ideal.out.v, '-g', label='Ideal', linewidth=1)
    plt.ylim(-0.66, 0.65)
    plt.xlim(10.3, 16.9)
    plt.legend(loc='lower left')
    plt.xlabel('Time (ns)')
    plt.ylabel('Value')
    plt.title('Transient Accuracy')

    plot_name = os.path.join(fig_dir, plot_prefix+'_emu_vs_ideal_comparison')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')

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
        fmt_dict_file = os.path.join(args.build_dir, 'fmt_dict.json')
        ila_dir_name = os.path.join(args.data_dir, 'ila', 'large_step')
        ila_data = IlaData(ila_dir_name=ila_dir_name, fmt_dict_file=fmt_dict_file)
        data = Data(tx=ila_data.tx.filter_in,
                    rxp=ila_data.rxp.filter_out,
                    rxn=ila_data.rxn.filter_out)

        plot_prefix = 'ila'
    else:
        data = get_sim_data(args.data_dir)
        plot_prefix = 'sim'

    ideal = get_ideal(rx_dyn=rx_dyn, tx=data.tx, rx_setting=args.rx_setting)

    report_error(data=data, ideal=ideal)

    plot_waveforms(data=data, ideal=ideal, fig_dir=args.fig_dir, plot_prefix=plot_prefix)
    
if __name__=='__main__':
    main()
