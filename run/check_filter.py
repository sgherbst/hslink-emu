import matplotlib.pyplot as plt
import numpy as np
import os.path

from numpy import genfromtxt
from scipy.interpolate import interp1d
from scipy.stats import describe

from msemu.ctle import RxDynamics
from msemu.pwl import Waveform
from msemu.cmd import get_parser

class SimResult:
    def __init__(self, pwl, ideal):
        self.pwl = pwl
        self.ideal = ideal

def eval(sim_dir, rx_dyn, rx_setting):
    # read data
    data = genfromtxt(os.path.join(sim_dir, 'filter_pwl_emu.txt'), delimiter=',')
    t_pwl = data[:, 0]
    v_pwl = data[:, 1]
    pwl = Waveform(t=t_pwl, v=v_pwl)

    # get ideal response
    ideal = rx_dyn.get_step(rx_setting)

    # return waveforms
    return SimResult(
        pwl = pwl,
        ideal = ideal
    )

def measure_error(result):
    test_idx = result.pwl.t <= result.ideal.t[-1]

    v_ideal_interp = interp1d(result.ideal.t, result.ideal.v)(result.pwl.t[test_idx])
    err = result.pwl.v[test_idx] - v_ideal_interp

    # compute percentage error
    plus_err = np.max(err) / result.ideal.yss
    minus_err = np.min(err) / result.ideal.yss

    print('relative error: {:+3e} / {:+3e}'.format(plus_err, minus_err))
    print('')
    print('error statistics: ')
    print(describe(err))

def plot(result):
    plt.plot(result.ideal.t, result.ideal.v, '-b', label='ideal')
    plt.plot(result.pwl.t, result.pwl.v, '-r', label='pwl')
    plt.ylim(-1.25, 1.25)
    plt.legend(loc='lower right')
    plt.xlabel('time')
    plt.ylabel('value')
    plt.show()

def main():
    parser = get_parser()
    parser.add_argument('--rx_setting', type=int, help='Setting of the RX CTLE.')
    args = parser.parse_args()

    # create the RxDynamics object
    rx_dyn = RxDynamics(dir_name=args.channel_dir)

    result = eval(sim_dir=args.sim_dir, rx_dyn=rx_dyn, rx_setting=args.rx_setting)

    measure_error(result)
    plot(result)
    
if __name__=='__main__':
    main()
