import numpy as np
from scipy.signal import fftconvolve
from scipy.interpolate import interp1d
from math import floor
import os.path
import sys
import logging
import re
from scipy.stats import describe

from msemu.ctle import RxDynamics
from msemu.pwl import Waveform
from msemu.cmd import get_parser
from msemu.ila import IlaData

class StatTracker:
    def __init__(self):
        self.worst_err_p = -float('inf')
        self.worst_err_n = float('inf')
        self.worst_err_dir_p = None
        self.worst_err_dir_n = None

    def read_waves(self, dir_name):
        try:
            emu_wave = Waveform.load(os.path.join(dir_name, 'emu.npy'))
        except:
            logging.debug('Could not find emulation waveform.')
            return

        try:
            ideal_wave = Waveform.load(os.path.join(dir_name, 'ideal.npy'))
        except:
            logging.debug('Could not find ideal waveform.')
            return

        # compute percentage error
        err = emu_wave.v - ideal_wave.v
        v_out_abs_max = np.max(np.abs(ideal_wave.v))
        plus_err = np.max(err) / v_out_abs_max
        minus_err = np.min(err) / v_out_abs_max

        if plus_err > self.worst_err_p:
            self.worst_err_p = plus_err
            self.worst_err_dir_p = dir_name

        if minus_err < self.worst_err_n:
            self.worst_err_n = minus_err
            self.worst_err_dir_n = dir_name

    def finish(self):
        print('Worst positive error: {:+0.3f} % @ {}'.format(self.worst_err_p*1e2, self.worst_err_dir_p))
        print('Worst negative error: {:+0.3f} % @ {}'.format(self.worst_err_n*1e2, self.worst_err_dir_n))

class Data:
    def __init__(self, tx, rxp, rxn):
        self.tx = tx
        self.rxp = rxp
        self.rxn = rxn

class IdealResult:
    def __init__(self, in_, out):
        self.in_ = in_
        self.out = out

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

def write_waves(data, ideal, dir_name):
    # compose list of times where the emulation output will be checked
    t_emu = np.concatenate((data.rxn.t, data.rxp.t))
    v_emu = np.concatenate((data.rxn.v, data.rxp.v))
    indices = t_emu <= ideal.out.t[-1]

    # construct emulation waveform
    emu_wave = Waveform(t=t_emu[indices], v=v_emu[indices])

    # compute ideal output at those times
    ideal_t = emu_wave.t
    ideal_v = interp1d(ideal.out.t, ideal.out.v)(ideal_t)
    ideal_wave = Waveform(t=ideal_t, v=ideal_v)

    # write results
    emu_wave.save(os.path.join(dir_name, 'emu'))
    ideal_wave.save(os.path.join(dir_name, 'ideal'))

    # print('error statistics: ')
    # print(describe(err))

def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    parser.add_argument('--write', action='store_true', help='Write error data.')
    parser.add_argument('--read', action='store_true', help='Read error data.')
    parser.add_argument('--restart', action='store_true', help='Read error data.')
    args = parser.parse_args()

    # create the RxDynamics object
    rx_dyn = RxDynamics(dir_name=args.channel_dir)

    fmt_dict_file = os.path.join(args.build_dir, 'fmt_dict.json')

    stat_tracker = StatTracker()

    sweep_dir = os.path.join(args.data_dir, 'ila', 'sweep')
    pat = re.compile(r'(\d+)_(\d+)')
    for filename in os.listdir(sweep_dir):
    #for filename in ['0_0']:
    #for filename in ['9_1']:
        if not os.path.isdir(os.path.join(sweep_dir, filename)):
            continue

        match = pat.match(filename)
        if match is not None:
            logging.debug('Visiting folder: {}'.format(filename))

            rx_setting = int(match.group(1))
            tx_setting = int(match.group(2))

            ila_dir_name = os.path.join(sweep_dir, filename)

            if args.write:
                if (args.restart or
                    (not os.path.isfile(os.path.join(ila_dir_name, 'emu.npy'))) or
                    (not os.path.isfile(os.path.join(ila_dir_name, 'ideal.npy')))):

                    ila_data = IlaData(ila_dir_name=ila_dir_name, fmt_dict_file=fmt_dict_file)
                    data = Data(tx=ila_data.tx.filter_in,
                                rxp=ila_data.rxp.filter_out,
                                rxn=ila_data.rxn.filter_out)

                    ideal = get_ideal(rx_dyn=rx_dyn, tx=ila_data.tx.filter_in, rx_setting=rx_setting)

                    write_waves(data=data, ideal=ideal, dir_name=ila_dir_name)
                else:
                    logging.debug('Skipping directory.')
            elif args.read:
                stat_tracker.read_waves(dir_name=ila_dir_name)

    if args.read:
        stat_tracker.finish()
    
if __name__=='__main__':
    main()