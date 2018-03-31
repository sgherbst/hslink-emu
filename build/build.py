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
import logging, sys

from msemu.rf import get_sample_s4p, s4p_to_impulse, imp2step
from msemu.pwl import Waveform, PWL
from msemu.fixed import Unsigned, Fixed, FixedSigned
from msemu.ctle import get_ctle_imp

class PulseResponse:
    def __init__(self, pwl, bias, offset_fmt, slope_fmt):
        self.pwl = pwl
        self.bias = bias
        self.offset_fmt = offset_fmt
        self.slope_fmt = slope_fmt

    @property
    def table_size_bits(self):
        return self.pwl.n * (self.offset_fmt.n + self.slope_fmt.n)

    def to_table_str(self):
        retval = []

        for offset, slope in zip(self.pwl.offsets, self.pwl.slopes):
            retval += self.offset_fmt.bin_str(offset - self.bias) + self.slope_fmt.bin_str(slope) + '\n'

        return retval

    def write_table(self, fname):
        table_str = self.to_table_str()
        with open(fname, 'w') as f:
            f.write(table_str)

    @staticmethod
    def make_pulse_resp(pwl, err_offset, err_slope):
        bias = (max(pwl.offsets) + min(pwl.offsets)) / 2
        offset_fmt = FixedSigned.get_format([max(pwl.offsets) - bias, min(pwl.offsets) - bias], err_offset)
        slope_fmt = FixedSigned.get_format([max(pwl.slopes), min(pwl.slopes)], err_slope / pwl.dtau)

        return PulseResponse(pwl=pwl, bias=bias, offset_fmt=offset_fmt, slope_fmt=slope_fmt)

def find_pwl(wave, t_start_intval, t_stop_intval, time_fmt, err_pwl, addr_bits_max=14):
    # round up number of time steps to next power of two
    n_steps_bits = Unsigned.get_bits(t_stop_intval - t_start_intval)

    # loop over the number of address bits
    addr_bits = 1
    while addr_bits <= addr_bits_max:
        # calculate step size
        table_step_bits = n_steps_bits-addr_bits
        dtau = Fixed.point2res(time_fmt.point - table_step_bits)

        # form a list of times for the PWL segments
        n_seg = 1<<addr_bits
        times = t_start_intval*time_fmt.res + np.arange(n_seg)*dtau

        pwl = wave.make_pwl(times=times)
        if pwl.error <= err_pwl:
            return pwl

        addr_bits += 1
    else:
        raise Exception('Failed to find a suitable PWL representation.')

def main():
    ###############################
    # User configuration
    dt = 1e-12
    T = 20e-9
    Fmin = 7.5e9
    Fmax = 8.5e9
    acc = 0.0025
    err_pwl = 1e-4
    err_offset = 1e-5
    err_slope = 1e-5
    err_time = 1e-5
    err_value = 1e-5
    db = -4
    R = 1
    ###############################

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    # Compute trimmed step response
    s4p = get_sample_s4p()
    t, imp_ch = s4p_to_impulse(s4p, dt, T)
    _, imp_ctle = get_ctle_imp(dt, T, db=db)
    imp_eff = fftconvolve(imp_ch, imp_ctle)[:len(t)]*dt
    step_eff = imp2step(imp=imp_eff, dt=dt)

    # trim step response based on accuracy settings
    step_orig = Waveform(t=t, v=step_eff)
    step_trim = step_orig.trim_settling(f_thresh=acc, rewind=1e-9)

    # Compute time format
    time_fmt = Fixed(point=Fixed.res2point(2e-15))
    Tmin_intval = time_fmt.float2fixed(val=1/Fmax, mode='floor')
    Tmax_intval = time_fmt.float2fixed(val=1/Fmin, mode='ceil')

    # Determine number of UIs required to ensure the full step response is covered
    num_ui = int(ceil(step_trim.t[-1] / (Tmin_intval * time_fmt.res))) + 1

    # Extend step response so that it can be evaluated anywhere where needed
    step_ext = step_trim.extend(Tmax=2*(num_ui*Tmax_intval)*time_fmt.res)

    pulse_resp_list = [None]*num_ui
    for k in range(num_ui):
        logging.debug('Building pulse response {}'.format(k))
        pwl = find_pwl(wave=step_ext, t_start_intval=k*Tmin_intval, t_stop_intval=(k+1)*Tmax_intval,
                       time_fmt=time_fmt, err_pwl=err_pwl)
        pulse_resp_list[k] = PulseResponse.make_pulse_resp(pwl=pwl, err_offset=err_offset, err_slope=err_slope)

    # Determine the time resolution for each pulse response
    time_points = np.zeros(num_ui)
    for k in range(num_ui-1,-1,-1):
        abs_slopes = np.abs(pulse_resp_list[k].pwl.slopes)
        max_abs_slope = np.max(abs_slopes)
        if max_abs_slope == 0:
            point = 0
        else:
            point = Fixed.res2point(err_time/max_abs_slope)
        if k==num_ui-1:
            time_points[k] = point
        else:
            time_points[k] = max(point, time_points[k+1])

    plt.plot(time_points)
    plt.show()

    Fmin = np.zeros(num_ui)
    Fmax = np.zeros(num_ui)
    for k in range(num_ui):
        pwl = pulse_resp_list[k].pwl
        Fmin[k] = min(pwl.offsets)
        Fmax[k] = max(pwl.offsets)

    Pmax = np.zeros(num_ui)
    for k in range(num_ui):
        if k==0:
            Pmax[k] = max(-Fmin[0], Fmax[0])
        else:
            Pmax[k] = max(Fmax[k]-Fmin[k-1], Fmax[k-1]-Fmin[k])

    value_points = np.zeros(num_ui)
    for k in range(num_ui - 1, -1, -1):
        if Pmax[k] == 0:
            point = 0
        else:
            point = Fixed.res2point(err_time / Pmax[k])
        if k == num_ui - 1:
            value_points[k] = point
        else:
            value_points[k] = max(point, value_points[k + 1])

    plt.plot(value_points)
    plt.show()

    # bits_per_pulse = np.array([elem.table_size_bits for elem in pulse_resp_list])
    # plt.plot(bits_per_pulse)
    # plt.show()
    #
    # plt.plot(step_ext.t, step_ext.v)
    #
    # for k in range(num_ui):
    #     pwl = pulse_resp_list[k].pwl
    #     t_eval = pwl.domain(dt)
    #     plt.plot(t_eval, pwl.eval(t_eval))
    #
    # plt.show()

if __name__=='__main__':
    main()
