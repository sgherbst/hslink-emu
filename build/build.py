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
from msemu.fixed import Unsigned, Fixed, FixedSigned, FixedUnsigned, Signed, Binary
from msemu.ctle import get_ctle_imp

class PwlTable:
    def __init__(self, pwl, addr_fmt, addr_offset_intval):
        self.pwl = pwl
        self.addr_fmt = addr_fmt
        self.addr_offset_intval = addr_offset_intval

        # leave these settings unitialized
        self.offset_fmt = None
        self.slope_fmt  = None
        self.bias_intval = None

    @property
    def table_size_bits(self):
        return self.pwl.n * (self.offset_fmt.n + self.slope_fmt.n)

    def to_table_str(self):
        retval = []

        offset_binary = Binary(n=self.offset_fmt.n)
        for offset, slope in zip(self.pwl.offsets, self.pwl.slopes):
            offset_biased_intval = self.offset_fmt.float2fixed(offset) - self.bias_intval
            retval += offset_binary.bin_str(offset_biased_intval) + self.slope_fmt.bin_str(slope) + '\n'

        return retval

    def write_table(self, fname):
        table_str = self.to_table_str()
        with open(fname, 'w') as f:
            f.write(table_str)

    def set_rom_fmt(self, err_offset, err_slope):
        # determine the offset format
        offset_point = Fixed.res2point(err_offset)
        offset_min_intval = Fixed.intval(min(self.pwl.offsets), point=offset_point)
        offset_max_intval = Fixed.intval(max(self.pwl.offsets), point=offset_point)

        # adjust using bias
        self.bias_intval = (offset_min_intval + offset_max_intval) // 2
        offset_min_intval -= self.bias_intval
        offset_max_intval -= self.bias_intval

        # create the offset format
        offset_bits = Signed.get_bits([offset_min_intval, offset_max_intval])
        self.offset_fmt = FixedSigned(n=offset_bits, point=offset_point)

        # determine slope format
        slope_range = [max(self.pwl.slopes), min(self.pwl.slopes)]
        self.slope_fmt = FixedSigned.get_format(slope_range, err_slope / self.pwl.dtau)

class ClockWithJitter:
    def __init__(self, freq, jitter, time_fmt):
        # compute jitter format
        max_jitter_intval = time_fmt.float2fixed(jitter, mode='round')
        self.jitter_fmt = FixedUnsigned(n=Unsigned.get_bits(max_jitter_intval), point=time_fmt.point)

        # compute main time format
        offset = (1/freq) - (jitter/2)
        self.offset_intval = time_fmt.float2fixed(offset, mode='round')

        # make sure the jitter isn't too large
        assert self.offset_intval > 0

    @property
    def Tmin_intval(self):
        return self.offset_intval + self.jitter_fmt.min

    @property
    def Tmax_intval(self):
        return self.offset_intval + self.jitter_fmt.max

class FilterBlock:
    def __init__(self):
        self.time_hist_fmt = None
        self.val_hist_fmt = None
        self.pwl_table = None

class FilterChain:
    def __init__(self, n):
        self.blocks = []
        for k in range(n):
            self.blocks.append(FilterBlock())

    @property
    def n(self):
        return len(self.blocks)

    def build_pwl_tables(self, Tmin_intval, Tmax_intval, wave, time_fmt, err_pwl):
        for k, block in enumerate(self.blocks):
            logging.debug('Building PWL #{}'.format(k))

            # compute time range for this filter block
            t_start_intval = k * Tmin_intval
            t_stop_intval = (k + 1) * Tmax_intval

            pwl_table = find_pwl_repr(wave=wave, t_start_intval=t_start_intval, t_stop_intval=t_stop_intval,
                                      time_fmt=time_fmt, err_pwl=err_pwl)

            self.blocks[k].pwl_table = pwl_table

    def set_rom_formats(self, err_offset, err_slope):
        for block in self.blocks:
            block.pwl_table.set_rom_fmt(err_offset=err_offset, err_slope=err_slope)

    def set_time_formats(self, err_time, T_diff_max_intval, time_fmt):
        # Determine the time formats of each pulse response
        for k in range(self.n - 1, -1, -1):
            block = self.blocks[k]

            # compute time resolution needed
            abs_slopes = np.abs(block.pwl_table.pwl.slopes)
            max_abs_slope = np.max(abs_slopes)
            if max_abs_slope == 0:
                my_time_point = 0
            else:
                my_time_point = Fixed.res2point(err_time/max_abs_slope)

            # Make sure that the given time format is actually sufficient
            assert time_fmt.point >= my_time_point, "Clock precision insufficient."

            # compute format
            T_diff_max_adj = T_diff_max_intval * (2**(my_time_point-time_fmt.point))
            my_time_width = int(ceil(log2(T_diff_max_adj+1)))
            my_time_fmt = FixedUnsigned(n=my_time_width, point=my_time_point)
            assert T_diff_max_intval <= ((1<<my_time_fmt.n)-1)*(1<<(time_fmt.point-my_time_fmt.point))

            # assign format
            if k==self.n-1:
                block.time_hist_fmt = my_time_fmt
            else:
                if my_time_fmt.point > self.blocks[k+1].time_hist_fmt.point:
                    block.time_hist_fmt = my_time_fmt
                else:
                    block.time_hist_fmt = self.blocks[k+1].time_hist_fmt

    def set_value_formats(self, err_value, R, dt=1e-12):
        # Determine the value format for each pulse response
        Fmin = np.zeros(self.n)
        Fmax = np.zeros(self.n)
        for k, block in enumerate(self.blocks):
            pwl = block.pwl_table.pwl
            resp = pwl.eval(pwl.domain(dt))
            Fmin[k] = np.min(resp)
            Fmax[k] = np.max(resp)

        for k in range(self.n - 1, -1, -1):
            block = self.blocks[k]

            if k == 0:
                max_pulse = max(-Fmin[0], Fmax[0])
            else:
                max_pulse = max(Fmax[k] - Fmin[k - 1], Fmax[k - 1] - Fmin[k])

            if max_pulse == 0:
                my_value_res = 1
            else:
                my_value_res = err_value / max_pulse

            # compute format
            my_value_fmt = FixedSigned.get_format([R, -R], my_value_res)
            if k == self.n - 1:
                block.value_hist_fmt = my_value_fmt
            else:
                if my_value_fmt.point > self.blocks[k + 1].value_hist_fmt.point:
                    block.value_hist_fmt = my_value_fmt
                else:
                    block.value_hist_fmt = self.blocks[k + 1].value_hist_fmt

def find_pwl_repr(wave, t_start_intval, t_stop_intval, time_fmt, err_pwl, addr_bits_max=14):
    # loop over the number of address bits
    addr_bits = 1

    while addr_bits <= addr_bits_max:
        # calculate table step size
        n_seg = 1<<addr_bits
        addr_point = int(floor(time_fmt.point-log2((t_stop_intval-t_start_intval+1)/(n_seg-1))))
        addr_fmt = FixedUnsigned(n=addr_bits, point=addr_point)

        # calculate the start time of the segment
        offset_intval = t_start_intval >> (time_fmt.point - addr_fmt.point)

        # make sure that the calculations are correct
        assert time_fmt.point >= addr_fmt.point
        int_fact = 1 << (time_fmt.point - addr_fmt.point)
        assert t_start_intval >= offset_intval * int_fact
        assert t_stop_intval <= (offset_intval + n_seg) * int_fact - 1

        # calculate a list of times for the segment start times
        times = (offset_intval + np.arange(n_seg))*addr_fmt.res

        # build pwl representation
        pwl = wave.make_pwl(times=times)
        if pwl.error <= err_pwl:
            return PwlTable(pwl=pwl, addr_fmt=addr_fmt, addr_offset_intval=offset_intval)

        addr_bits += 1
    else:
        raise Exception('Failed to find a suitable PWL representation.')

def get_combined_step(db=-4, dt=1e-12, T=20e-9):
    s4p = get_sample_s4p()
    t, imp_ch = s4p_to_impulse(s4p, dt, T)
    _, imp_ctle = get_ctle_imp(dt, T, db=db)
    imp_eff = fftconvolve(imp_ch, imp_ctle)[:len(t)]*dt
    step_eff = imp2step(imp=imp_eff, dt=dt)

    return Waveform(t=t, v=step_eff)

def main():
    ###############################
    # User configuration
    ###############################

    # system settings
    Temu = 1e-3 # maximum emulation time
    Fnom = 8e9 # nominal TX frequency
    jitter = 10e-12 # peak-to-peak jitter of TX
    db = -4 # equalization setting of RX CTLE
    R = 1 # input range

    # error settings
    t_res = 1e-14 # smallest time resolution represented in the system
    err_trunc = 0.0025 # percent settling at which the step response is truncated
    err_pwl = 1e-4 # error due to approximation of a continuous waveform by segments
    err_offset = 1e-4 # error due to quantization of PWL offset
    err_slope = 1e-4 # error due to quantization of PWL slope
    err_time = 1e-4 # error due to quantization of input history time
    err_value = 1e-4 # error due to quantization of input history value
    ###############################

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    # Compute step response of channel and CTLE
    step_orig = get_combined_step(db=db)

    # Trim step response based on accuracy settings
    step_trim = step_orig.trim_settling(f_thresh=err_trunc, rewind=1e-9)

    # Compute time format
    time_fmt = FixedUnsigned.get_format(Temu, res=t_res)
    clk_tx = ClockWithJitter(freq=Fnom, jitter=jitter, time_fmt=time_fmt)

    # Determine number of UIs required to ensure the full step response is covered
    num_ui = int(ceil(step_trim.t[-1] / (clk_tx.Tmin_intval * time_fmt.res))) + 1

    # Extend step response so that it can be evaluated anywhere where needed
    step_ext = step_trim.extend(Tmax=2*(num_ui*clk_tx.Tmax_intval)*time_fmt.res)

    # Build up a list of filter blocks
    filter = FilterChain(num_ui)

    # Build the PWL tables
    filter.build_pwl_tables(Tmin_intval=clk_tx.Tmin_intval, Tmax_intval=clk_tx.Tmax_intval,
                            wave=step_ext, time_fmt=time_fmt, err_pwl=err_pwl)
    filter.set_rom_formats(err_offset=err_offset, err_slope=err_slope)

    # Determine the time formats along the filter chain
    T_diff_max_intval = (num_ui+1)*clk_tx.Tmax_intval
    filter.set_time_formats(err_time=err_time, T_diff_max_intval=T_diff_max_intval, time_fmt=time_fmt)

    # Determine the value formats along the chain
    filter.set_value_formats(err_value=err_value, R=R)

    bits_per_time = np.array([block.time_hist_fmt.n for block in filter.blocks])
    bits_per_value = np.array([block.value_hist_fmt.n for block in filter.blocks])
    plt.plot(np.arange(filter.n), bits_per_time, label='time')
    plt.plot(np.arange(filter.n), bits_per_value, label='value')
    plt.xlabel('Step Response #')
    plt.ylabel('Bits')
    plt.legend()
    plt.show()

    bits_per_pulse = np.array([block.pwl_table.table_size_bits for block in filter.blocks])
    plt.plot(bits_per_pulse)
    plt.xlabel('Step Response #')
    plt.ylabel('ROM Bits')
    plt.show()

    # plt.plot(step_ext.t, step_ext.v)
    #
    # for block in filter.blocks:
    #     pwl = block.pwl_table.pwl
    #     t_eval = pwl.domain(step_ext.dt)
    #     plt.plot(t_eval, pwl.eval(t_eval))
    #
    # plt.show()

if __name__=='__main__':
    main()
