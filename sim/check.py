from numpy import genfromtxt, convolve
import matplotlib.pyplot as plt
import argparse
import numpy as np
from scipy.signal import lsim, impulse, tf2ss, fftconvolve
from scipy.interpolate import interp1d
from scipy.stats import describe
from math import exp, log, ceil, floor, pi, log2, sqrt
import subprocess
from scipy.linalg import matrix_balance, svd, norm, expm
from numpy.linalg import lstsq, solve, inv
import cvxpy

class SimResult:
    pass

def eval_single(args):
    # object to hold return data
    retval = SimResult()

    # read tx data
    data_tx = genfromtxt('tx.txt', delimiter=',')
    t_tx = data_tx[:, 0]
    v_tx = data_tx[1:, 1]
    v_tx = np.concatenate((v_tx, [v_tx[-1]]))
    
    # read rxp data (positive clock edge sampling)
    data_rxp = genfromtxt('rxp.txt', delimiter=',')
    retval.t_rxp = data_rxp[:, 0]
    retval.v_rxp = data_rxp[:, 1]
    
    # read rxn data (negative clock edge sampling)
    data_rxn = genfromtxt('rxn.txt', delimiter=',')
    retval.t_rxn = data_rxn[:, 0]
    retval.v_rxn = data_rxn[:, 1]

    # get step response of channel
    t_ch, v_ch = get_rx_step(rx_preset=args.rx_preset)

    # interpolate channel response and input waveform
    dt = args.time_res
    retval.t_ch_imp = np.arange(int(floor(t_ch[-1]/dt + 1)))*dt
    retval.t_in_sim = np.arange(int(floor(t_tx[-1]/dt + 1)))*dt

    # simulate system response
    retval.v_ch_stp = (interp1d(t_ch, v_ch)(retval.t_ch_imp))
    retval.v_ch_imp = np.diff(retval.v_ch_stp)
    retval.v_in_sim = interp1d(t_tx, v_tx, kind='zero')(retval.t_in_sim)
    retval.v_out_sim = fftconvolve(retval.v_in_sim, retval.v_ch_imp)[:len(retval.t_in_sim)]
    retval.t_out_sim = retval.t_in_sim

    # return waveforms
    return retval

def measure_error_single(obj):
    t_emu = np.concatenate((obj.t_rxn, obj.t_rxp))
    v_emu = np.concatenate((obj.v_rxn, obj.v_rxp))
    test_idx = t_emu <= obj.t_out_sim[-1]

    v_sim_interp = interp1d(obj.t_out_sim, obj.v_out_sim)(t_emu[test_idx])
    err = v_emu[test_idx] - v_sim_interp

    return err

def plot_single(obj):
    print('Maximum absolute value of waveform:', np.max(np.abs(obj.v_out_sim)))

    plt.step(obj.t_in_sim, obj.v_in_sim, '-k', where='post', label='in')
    plt.plot(obj.t_rxp, obj.v_rxp, 'b*', label='rxp')
    plt.plot(obj.t_rxn, obj.v_rxn, 'ro', label='rxn')
    plt.plot(obj.t_out_sim, obj.v_out_sim, '-g', label='sim')
    plt.ylim(-1.25, 1.25)
    plt.legend(loc='lower right')
    plt.xlabel('time')
    plt.ylabel('value')
    plt.show()

def run_wave(args):
    # prepare simulation
    # note that some of args are adjusted by this function
    var_dict = prepare_sim(args)

    # run simulation
    run_sim('sys_test.sv', var_dict)

    if args.run_mode.lower() in ['short']:
        # parse results
        obj = eval_single(args, var_dict)

        err = measure_error_single(obj)

        # plot results
        if args.show:
            print('error statistics: ')
            print(describe(err))
            plot_single(obj)

        return err
    
    else:
        return None

def main():
    pass
    
if __name__=='__main__':
    main()
