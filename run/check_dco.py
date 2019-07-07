import os.path
import matplotlib.pyplot as plt
import numpy as np

from numpy import genfromtxt
from scipy.interpolate import interp1d
from scipy.stats import describe

from msemu.clocks import RxClock
from msemu.pwl import Waveform
from msemu.cmd import get_parser
from msemu.fixed import Fixed

class SimResult:
    def __init__(self, pwl, ideal):
        self.pwl = pwl
        self.ideal = ideal

def eval(sim_dir):
    # read data
    data = genfromtxt(os.path.join(sim_dir, 'dco_pwl_emu.txt'), delimiter=',')
    t_pwl = data[:, 0]
    v_pwl = data[:, 1]
    pwl = Waveform(t=t_pwl, v=v_pwl)

    # get ideal response
    time_fmt = Fixed.make([0, 10e-3], 1e-14, signed=False)
    clk_rx = RxClock(fmin=7.5e9, fmax=8.5e9, bits=14, jitter_pkpk_max=2e-12, time_fmt=time_fmt)
    ideal = clk_rx.dco_tf 

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
    plus_err = np.max(err) 
    minus_err = np.min(err) 

    print('error: {:+0.3f} ps / {:+0.3f} ps'.format(plus_err*1e12, minus_err*1e12))
    print('')
    print('error statistics: ')
    print(describe(err))

def plot(result):
    plt.plot(result.ideal.t, result.ideal.v, '-b', label='ideal')
    plt.plot(result.pwl.t, result.pwl.v, '-r', label='pwl')
    plt.legend(loc='lower right')
    plt.xlabel('code')
    plt.ylabel('period')
    plt.show()

def main():
    parser = get_parser()
    args = parser.parse_args()

    result = eval(sim_dir=args.sim_dir)
    measure_error(result)
    plot(result)
    
if __name__=='__main__':
    main()
