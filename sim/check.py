from numpy import genfromtxt
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import fftconvolve
from scipy.interpolate import interp1d
from scipy.stats import describe
from math import floor
import os.path
import sys

from msemu.ctle import get_ctle_imp
from msemu.rf import get_sample_s4p, s4p_to_impulse
from msemu.pwl import Waveform

class SimResult:
    def __init__(self, tx, rxp, rxn, imp, in_, out):
        self.tx = tx
        self.rxp = rxp
        self.rxn = rxn
        self.imp = imp
        self.in_ = in_
        self.out = out

def get_imp_eff():
    # get the exact step response used in the build script
    import_path = os.path.dirname(os.path.realpath(__file__))
    import_path = os.path.join(import_path, os.path.pardir, 'build')
    import_path = os.path.realpath(import_path)
    print(import_path)
    sys.path.append(import_path)
    from build.build import get_combined_step

    # compute the impulse response
    step, _ = get_combined_step()
    v_new = np.diff(step.v)/step.dt
    t_new = step.t[:-1]    

    return Waveform(t=t_new, v=v_new)

def eval():
    # read tx data
    data_tx = genfromtxt('tx.txt', delimiter=',')
    t_tx = data_tx[:, 0]
    v_tx = data_tx[1:, 1]
    v_tx = np.concatenate((v_tx, [v_tx[-1]]))
    tx = Waveform(t=t_tx, v=v_tx)
    
    # read rxp data (positive clock edge sampling)
    data_rxp = genfromtxt('rxp.txt', delimiter=',')
    rxp = Waveform(t=data_rxp[:, 0], v=data_rxp[:, 1])
    
    # read rxn data (negative clock edge sampling)
    data_rxn = genfromtxt('rxn.txt', delimiter=',')
    rxn = Waveform(t=data_rxn[:, 0], v=data_rxn[:, 1])

    # get impulse response of channel
    imp = get_imp_eff()

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
    plus_err = np.max(err)/v_out_abs_max
    minus_err = np.min(err) / v_out_abs_max

    print('error: {:+3f} / {:+3f} %'.format(plus_err*1e2, minus_err*1e2))
    print('')
    print('error statistics: ')
    print(describe(err))

    return err

def plot(result):
    plt.step(result.in_.t, result.in_.v, '-k', where='post', label='in')
    plt.plot(result.rxp.t, result.rxp.v, 'b*', label='rxp')
    plt.plot(result.rxn.t, result.rxn.v, 'ro', label='rxn')
    plt.plot(result.out.t, result.out.v, '-g', label='sim')
    plt.ylim(-1.25, 1.25)
    plt.legend(loc='lower right')
    plt.xlabel('time')
    plt.ylabel('value')
    plt.show()

def main():
    result = eval()

    measure_error(result)
    plot(result)
    
if __name__=='__main__':
    main()
