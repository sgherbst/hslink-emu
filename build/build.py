import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import fftconvolve
from math import ceil, floor, log2
import logging, sys
import os.path

from msemu.rf import get_sample_s4p, s4p_to_impulse, imp2step
from msemu.pwl import Waveform
from msemu.fixed import Unsigned, Fixed, FixedSigned, FixedUnsigned, Signed, Binary
from msemu.ctle import get_ctle_imp
from msemu.verilog import VerilogPackage, DefineVariable, VerilogTypedef

class ErrorBudget:
    def __init__(self,
                 err_trunc = 0.01, # residual settling error (%)
                 err_pwl = 1e-4, # error due to approximation of a continuous waveform by segments
                 err_offset = 1e-4, # error due to quantization of PWL offset
                 err_slope = 1e-4, # error due to quantization of PWL slope
                 err_time = 1e-4, # error due to quantization of input history time
                 err_value = 1e-4, # error due to quantization of input history value
                 err_out = 1e-4, # error due to representation of output
    ):
        self.err_trunc = err_trunc
        self.err_pwl = err_pwl
        self.err_offset = err_offset
        self.err_slope = err_slope
        self.err_time = err_time
        self.err_value = err_value
        self.err_out = err_out

def main(db=-4, plot_dt=1e-12):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    err = ErrorBudget()
    emu = Emulation(err=err)
    step_ext = emu.build_filter_chain(db=db)

    emu.write_filter_rom_files()
    emu.write_filter_package()

    emu.write_time_package()
    emu.write_signal_package()

    # Plot bits used in history
    bits_per_time = np.array([block.time_hist_fmt.n for block in emu.filter.blocks])
    bits_per_value = np.array([block.value_hist_fmt.n for block in emu.filter.blocks])
    plt.plot(np.arange(emu.filter.n), bits_per_time, label='time')
    plt.plot(np.arange(emu.filter.n), bits_per_value, label='value')
    plt.xlabel('Step Response #')
    plt.ylabel('Bits')
    plt.legend()
    plt.savefig('history_bits.pdf')
    plt.clf()

    # Print information about DFF utilization
    time_hist_dff = np.sum(bits_per_time)
    value_hist_dff = np.sum(bits_per_value)
    time_hist_orig = emu.filter.n * bits_per_time[0]
    value_hist_orig = emu.filter.n * bits_per_value[0]
    time_hist_pct = 100 * (time_hist_orig-time_hist_dff)/time_hist_orig
    value_hist_pct = 100 * (value_hist_orig - value_hist_dff) / value_hist_orig
    print('*** DFF utilization estimate ***')
    print('Time hist DFFs: {} (non-opt: {}; {:0.1f}% lower)'.format(time_hist_dff, time_hist_orig, time_hist_pct))
    print('Value hist DFFs: {} (non-opt: {}; {:0.1f}% lower)'.format(value_hist_dff, value_hist_orig, value_hist_pct))

    # Plot bits used for PWL ROMs
    bits_per_pulse = np.array([block.pwl_table.table_size_bits for block in emu.filter.blocks])
    plt.plot(bits_per_pulse)
    plt.xlabel('Step Response #')
    plt.ylabel('ROM Bits')
    plt.savefig('rom_bits.pdf')
    plt.clf()

    # Plot number of segments for PWLs
    seg_per_pulse = np.array([block.pwl_table.pwl.n for block in emu.filter.blocks])
    plt.plot(seg_per_pulse)
    plt.xlabel('Step Response #')
    plt.ylabel('PWL Segments')
    plt.savefig('pwl_segments.pdf')
    plt.clf()

    # Plot number of segments for PWLs
    data_width_per_pulse = np.array([block.pwl_table.offset_fmt.n+block.pwl_table.slope_fmt.n for block in emu.filter.blocks])
    plt.plot(data_width_per_pulse)
    plt.xlabel('Step Response #')
    plt.ylabel('Data Width')
    plt.savefig('pwl_data_width.pdf')
    plt.clf()

    # Plot step response
    plt.plot(step_ext.t, step_ext.v)

    for block in emu.filter.blocks:
        pwl = block.pwl_table.pwl
        t_eval = pwl.domain(plot_dt)
        plt.plot(t_eval, pwl.eval(t_eval))
    plt.xlabel('Time')
    plt.ylabel('Value')
    plt.savefig('step_resp.pdf')
    plt.clf()

def my_rshift(val, amt):
    if amt < 0:
        return val << (-amt)
    else:
        return val >> amt

class Emulation:
    def __init__(self,
                 err, # error budget
                 Tstop = 4e-9, # stopping time of emulation
                 Fnom = 8e9, # nominal TX frequency
                 jitter = 10e-12, # peak-to-peak jitter of TX
                 R = 1, # input range
                 t_res = 1e-14 # smallest time resolution represented
    ):
        self.err = err
        self.Tstop = Tstop
        self.Fnom = Fnom
        self.jitter = jitter
        self.R = R
        self.t_res = t_res

        # Compute time format
        self.time_fmt = FixedUnsigned.get_format(self.Tstop, res=self.t_res)
        self.clk_tx = ClockWithJitter(freq=self.Fnom, jitter=self.jitter, time_fmt=self.time_fmt)
        self.clk_rx = ClockWithJitter(freq=self.Fnom, jitter=self.jitter, time_fmt=self.time_fmt, phases=2)

        # Placeholders
        self.dco = None
        self.filter = None

    def build_filter_chain(self, db=-4):
        # Compute step response of channel and CTLE
        step_orig = get_combined_step(db=db)

        # Trim step response based on accuracy settings
        step_trim = step_orig.trim_settling(thresh=self.err.err_trunc)

        # Determine number of UIs required to ensure the full step response is covered
        num_ui = int(ceil(step_trim.t[-1] / (self.clk_tx.Tmin_intval * self.time_fmt.res))) + 1

        # Extend step response so that it can be evaluated anywhere where needed
        step_ext = step_trim.extend(Tmax=2 * (num_ui * self.clk_tx.Tmax_intval) * self.time_fmt.res)

        # Build up a list of filter blocks
        self.filter = FilterChain(num_ui)

        # Build the PWL tables
        self.filter.build_pwl_tables(Tmin_intval=self.clk_tx.Tmin_intval, Tmax_intval=self.clk_tx.Tmax_intval,
                                     wave=step_ext, time_fmt=self.time_fmt, error_budget=self.err)
        self.filter.set_rom_formats(error_budget=self.err)

        # Determine the time formats along the filter chain
        T_diff_max_intval = (num_ui + 1) * self.clk_tx.Tmax_intval
        self.filter.set_time_formats(T_diff_max_intval=T_diff_max_intval, time_fmt=self.time_fmt,
                                      error_budget=self.err)

        # Determine the value formats along the chain
        self.filter.set_value_formats(R=self.R, error_budget=self.err)

        # Set the format of pulse bias
        self.filter.set_pulse_bias_formats()
        self.filter.set_pulse_formats()
        self.filter.set_prod_formats(R=self.R, error_budget=self.err)
        self.filter.set_out_format()

        return step_ext

    def write_filter_rom_files(self, dir='roms', prefix='filter_rom_', suffix='.mem'):
        self.filter_rom_names = [None]*self.filter.n
        for k, block in enumerate(self.filter.blocks):
            self.filter_rom_names[k] = prefix + str(k) + suffix
            block.pwl_table.write_table(os.path.join(dir, self.filter_rom_names[k]))

    def write_filter_package(self, name='filter_settings'):
        pack = VerilogPackage(name=name)

        # number of UI

        pack.add(DefineVariable(name='NUM_UI', value=self.filter.n, kind='int'))

        # time history formatting

        pack.add(DefineVariable(name='TIME_HIST_WIDTHS',
                                value=[block.time_hist_fmt.n for block in self.filter.blocks],
                                kind='int'))

        pack.add(DefineVariable(name='TIME_HIST_POINTS',
                                value=[block.time_hist_fmt.point for block in self.filter.blocks],
                                kind='int'))

        # value history formatting

        pack.add(DefineVariable(name='VALUE_HIST_WIDTHS',
                                value=[block.value_hist_fmt.n for block in self.filter.blocks],
                                kind='int'))

        pack.add(DefineVariable(name='VALUE_HIST_POINTS',
                                value=[block.value_hist_fmt.point for block in self.filter.blocks],
                                kind='int'))

        # ROM file names
        pack.add(DefineVariable(name='PWL_ROM_NAMES',
                                value=self.filter_rom_names,
                                kind='string'))

        # ROM address formats
        pack.add(DefineVariable(name='PWL_ADDR_WIDTHS',
                                value=[block.pwl_table.addr_fmt.n for block in self.filter.blocks],
                                kind='int'))
        pack.add(DefineVariable(name='PWL_ADDR_POINTS',
                                value=[block.pwl_table.addr_fmt.point for block in self.filter.blocks],
                                kind='int'))

        # ROM address bias
        pack.add(DefineVariable(name='PWL_ADDR_OFFSET_VALS',
                                value=[block.pwl_table.addr_offset_intval for block in self.filter.blocks],
                                kind='longint'))

        # pwl offset formatting

        pack.add(DefineVariable(name='PWL_OFFSET_WIDTHS',
                                value=[block.pwl_table.offset_fmt.n for block in self.filter.blocks],
                                kind='int'))

        pack.add(DefineVariable(name='PWL_OFFSET_POINTS',
                                value=[block.pwl_table.offset_fmt.point for block in self.filter.blocks],
                                kind='int'))

        # pwl slope formatting

        pack.add(DefineVariable(name='PWL_SLOPE_WIDTHS',
                                value=[block.pwl_table.slope_fmt.n for block in self.filter.blocks],
                                kind='int'))

        pack.add(DefineVariable(name='PWL_SLOPE_POINTS',
                                value=[block.pwl_table.slope_fmt.point for block in self.filter.blocks],
                                kind='int'))

        # pwl output formatting
        pack.add(DefineVariable(name='PWL_LIN_CORR_WIDTHS',
                                value=[block.pwl_table.lin_corr_width for block in self.filter.blocks],
                                kind='int'))

        pwl_out_widths = [block.pwl_table.output_width for block in self.filter.blocks]
        pack.add(DefineVariable(name='PWL_OUT_WIDTHS',
                                value=pwl_out_widths,
                                kind='int'))

        pack.add(DefineVariable(name='MAX_PWL_OUT_WIDTH',
                                value=max(pwl_out_widths),
                                kind='int'))

        # pulse formatting

        pack.add(DefineVariable(name='PULSE_OFFSET_VALS',
                                value=[pulse_bias_intval for pulse_bias_intval in self.filter.pulse_bias_intvals],
                                kind='longint'))

        pack.add(DefineVariable(name='PULSE_OFFSET_POINTS',
                                value=[pulse_bias_width for pulse_bias_width in self.filter.pulse_bias_widths],
                                kind='int'))

        pack.add(DefineVariable(name='PULSE_TERM_WIDTHS',
                                value=[pulse_term_width for pulse_term_width in self.filter.pulse_term_widths],
                                kind='int'))

        pack.add(DefineVariable(name='PULSE_WIDTHS',
                                value=[pulse_width for pulse_width in self.filter.pulse_widths],
                                kind='int'))

        pack.add(DefineVariable(name='MAX_PULSE_WIDTH',
                                value=max(self.filter.pulse_widths),
                                kind='int'))

        # product formatting

        pack.add(DefineVariable(name='PRODUCT_WIDTH',
                                value=max(self.filter.prod_widths),
                                kind='int'))

        # output formatting

        pack.add(DefineVariable(name='OUT_WIDTH',
                                value=self.filter.out_fmt.n,
                                kind='int'))

        pack.add(DefineVariable(name='OUT_POINT',
                                value=self.filter.out_fmt.point,
                                kind='int'))

        # write package to file

        pack.write_to_file(name + '.sv')

    def write_time_package(self, name='time_settings'):
        pack = VerilogPackage(name=name)

        pack.add(DefineVariable(name='TIME_WIDTH', value=self.time_fmt.n, kind='int'))
        pack.add(DefineVariable(name='TIME_POINT', value=self.time_fmt.point, kind='int'))
        pack.add(DefineVariable(name='TIME_STOP', value=self.time_fmt.float2fixed(self.Tstop), kind='longint'))

        pack.add(VerilogTypedef(name='time_t', width=self.time_fmt.n))

        pack.add(DefineVariable(name='TX_INC', value=self.clk_tx.offset_intval, kind='longint'))
        pack.add(DefineVariable(name='RX_INC', value=self.clk_rx.offset_intval, kind='longint'))

        pack.write_to_file(name + '.sv')

    def write_signal_package(self, name='signal_settings'):
        pack = VerilogPackage(name=name)

        pack.add(DefineVariable(name='SIGNAL_WIDTH', value=self.filter.out_fmt.n, kind='int'))
        pack.add(DefineVariable(name='SIGNAL_POINT', value=self.filter.out_fmt.point, kind='int'))

        pack.add(VerilogTypedef(name='signal_t', width=self.filter.out_fmt.n, signed=True))

        pack.write_to_file(name + '.sv')

class PwlTable:
    def __init__(self, pwl, addr_fmt, addr_offset_intval):
        self.pwl = pwl
        self.addr_fmt = addr_fmt
        self.addr_offset_intval = addr_offset_intval

        # leave these settings unitialized
        self.offset_fmt = None
        self.slope_fmt  = None
        self.bias_intval = None
        self.slope_intvals = None
        self.offset_biased_intvals = None

    def lin_corr_intval(self, slope_intval):
        return my_rshift(slope_intval, self.addr_fmt.point + self.slope_fmt.point - self.offset_fmt.point)

    @property
    def lin_corr_width(self):
        lin_corr_intvals = [self.lin_corr_intval(slope_intval) for slope_intval in self.slope_intvals]
        lin_corr_intval_min = min(lin_corr_intvals)
        lin_corr_intval_max = max(lin_corr_intvals)
        return Signed.get_bits([lin_corr_intval_min, lin_corr_intval_max])

    @property
    def output_width(self):
        return Signed.get_bits([self.biased_intval_min(), self.biased_intval_max()])

    @property
    def last_point_intval(self):
        return self.offset_biased_intvals[-1] + self.lin_corr_intval(self.slope_intvals[-1])

    def biased_intval_min(self):
        return min(self.offset_biased_intvals + [self.last_point_intval])

    def biased_intval_max(self):
        return max(self.offset_biased_intvals + [self.last_point_intval])

    @property
    def table_size_bits(self):
        return self.pwl.n * (self.offset_fmt.n + self.slope_fmt.n)

    def to_table_str(self):
        retval = ''

        offset_binary = Binary(n=self.offset_fmt.n)
        slope_binary = Binary(n=self.slope_fmt.n)
        for offset_biased_intval, slope_intval in zip(self.offset_biased_intvals, self.slope_intvals):
            retval += offset_binary.bin_str(offset_biased_intval) + slope_binary.bin_str(slope_intval) + '\n'

        return retval

    def write_table(self, fname):
        table_str = self.to_table_str()
        with open(fname, 'w') as f:
            f.write(table_str)

    def set_rom_fmt(self, error_budget):
        # determine the offset format
        offset_point = Fixed.res2point(error_budget.err_offset)
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
        self.slope_fmt = FixedSigned.get_format(slope_range, error_budget.err_slope / self.pwl.dtau)

        # generate fixed point data
        self.offset_biased_intvals = [0]*self.pwl.n
        self.slope_intvals = [0]*self.pwl.n
        for k in range(self.pwl.n):
            self.offset_biased_intvals[k] = self.offset_fmt.float2fixed(self.pwl.offsets[k]) - self.bias_intval
            self.slope_intvals[k] = self.slope_fmt.float2fixed(self.pwl.slopes[k])

class ClockWithJitter:
    def __init__(self, freq, jitter, time_fmt, phases=1):
        # compute jitter format
        max_jitter_intval = time_fmt.float2fixed(jitter, mode='round')
        self.jitter_fmt = FixedUnsigned(n=Unsigned.get_bits(max_jitter_intval), point=time_fmt.point)

        # compute main time format
        offset = (1/(phases*freq)) - (jitter/2)
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

    def build_pwl_tables(self, Tmin_intval, Tmax_intval, wave, time_fmt, error_budget):
        for k, block in enumerate(self.blocks):
            logging.debug('Building PWL #{}'.format(k))

            # compute time range for this filter block
            t_start_intval = k * Tmin_intval
            t_stop_intval = (k + 1) * Tmax_intval

            pwl_table = find_pwl_repr(wave=wave, t_start_intval=t_start_intval, t_stop_intval=t_stop_intval,
                                      time_fmt=time_fmt, error_budget=error_budget)

            self.blocks[k].pwl_table = pwl_table

    def set_rom_formats(self, error_budget):
        for block in self.blocks:
            block.pwl_table.set_rom_fmt(error_budget=error_budget)

    def set_time_formats(self, T_diff_max_intval, time_fmt, error_budget):
        # Determine the time formats of each pulse response
        for k in range(self.n - 1, -1, -1):
            block = self.blocks[k]

            # compute time resolution needed
            abs_slopes = np.abs(block.pwl_table.pwl.slopes)
            max_abs_slope = np.max(abs_slopes)
            if max_abs_slope == 0:
                my_time_point = 0
            else:
                my_time_point = Fixed.res2point(error_budget.err_time/max_abs_slope)

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

    def set_value_formats(self, R, error_budget, dt=1e-12):
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
                my_value_res = error_budget.err_value / max_pulse

            # compute format
            my_value_fmt = FixedSigned.get_format([R, -R], my_value_res)
            if k == self.n - 1:
                block.value_hist_fmt = my_value_fmt
            else:
                if my_value_fmt.point > self.blocks[k + 1].value_hist_fmt.point:
                    block.value_hist_fmt = my_value_fmt
                else:
                    block.value_hist_fmt = self.blocks[k + 1].value_hist_fmt

    def set_pulse_bias_formats(self):
        pwl_bias_intvals = [block.pwl_table.bias_intval for block in self.blocks]
        pwl_bias_points = [block.pwl_table.offset_fmt.point for block in self.blocks]

        self.pulse_bias_intvals = [0]*self.n
        self.pulse_bias_points = [0]*self.n
        self.pulse_bias_widths = [0]*self.n

        for k in range(self.n):
            if k == 0:
                pulse_bias_point = pwl_bias_points[k]
                pulse_bias_intval = pwl_bias_intvals[k]
            else:
                pulse_bias_point = max(pwl_bias_points[k], pwl_bias_points[k - 1])
                pulse_bias_intval = ((pwl_bias_intvals[k] << (pulse_bias_point - pwl_bias_points[k])) -
                                     (pwl_bias_intvals[k - 1] << (pulse_bias_point - pwl_bias_points[k - 1])))
            pulse_bias_width = Signed.get_bits(pulse_bias_intval)

            self.pulse_bias_intvals[k] = pulse_bias_intval
            self.pulse_bias_points[k] = pulse_bias_point
            self.pulse_bias_widths[k] = pulse_bias_width

    def set_pulse_formats(self):
        # Set the format of pulses
        self.pulse_widths = [0]*self.n
        self.pulse_min_intvals = [0]*self.n
        self.pulse_max_intvals = [0]*self.n
        self.pulse_term_widths = [0]*self.n

        for k in range(self.n):
            if k==0:
                pulse_min_intval = (self.pulse_bias_intvals[k]
                                    + self.blocks[k].pwl_table.biased_intval_min())
                pulse_max_intval = (self.pulse_bias_intvals[k]
                                    + self.blocks[k].pwl_table.biased_intval_max())
                pulse_terms_extreme = [pulse_min_intval, pulse_max_intval]
            else:
                # point formatting
                old_point_p = self.blocks[k].pwl_table.offset_fmt.point
                old_point_m = self.blocks[k-1].pwl_table.offset_fmt.point
                new_point = self.pulse_bias_points[k]

                # extreme values from both PWLs
                intval_max_p = self.blocks[k].pwl_table.biased_intval_max() # on offset format
                intval_min_p = self.blocks[k].pwl_table.biased_intval_min() # on offset format
                intval_max_m = self.blocks[k-1].pwl_table.biased_intval_max() # on offset format
                intval_min_m = self.blocks[k-1].pwl_table.biased_intval_min() # on offset format

                pulse_terms_extreme = [intval_max_p, intval_min_p, intval_max_m, intval_min_m]

                pulse_min_intval = (self.pulse_bias_intvals[k]
                                    + my_rshift(intval_min_p, old_point_p - new_point)
                                    - my_rshift(intval_max_m, old_point_m - new_point))
                pulse_max_intval = (self.pulse_bias_intvals[k]
                                    + my_rshift(intval_max_p, old_point_p - new_point)
                                    - my_rshift(intval_min_m, old_point_m - new_point))

            self.pulse_min_intvals[k] = pulse_min_intval
            self.pulse_max_intvals[k] = pulse_max_intval
            self.pulse_widths[k] = Signed.get_bits([self.pulse_min_intvals[k], self.pulse_max_intvals[k]])
            self.pulse_term_widths[k] = Signed.get_bits(pulse_terms_extreme)

    def set_prod_formats(self, R, error_budget):
        self.out_fmt_point = Fixed.res2point(error_budget.err_out)
        self.prod_min_intvals = [0]*self.n
        self.prod_max_intvals = [0]*self.n
        self.prod_widths = [0]*self.n

        prod_points = [0]*self.n
        for k in range(self.n):
            in_min_intval = self.blocks[k].value_hist_fmt.float2fixed(-R, mode='floor')
            in_max_intval = self.blocks[k].value_hist_fmt.float2fixed(+R, mode='ceil')
            pulse_min_intval = self.pulse_min_intvals[k]
            pulse_max_intval = self.pulse_max_intvals[k]
            prods = [in_min_intval*pulse_min_intval,
                     in_max_intval*pulse_min_intval,
                     in_min_intval*pulse_max_intval,
                     in_max_intval*pulse_max_intval]
            prod_points[k] = self.blocks[k].value_hist_fmt.point + self.blocks[k].pwl_table.offset_fmt.point

            self.prod_min_intvals[k] = my_rshift(min(prods), prod_points[k] - self.out_fmt_point)
            self.prod_max_intvals[k] = my_rshift(max(prods), prod_points[k] - self.out_fmt_point)

            self.prod_widths[k] = Signed.get_bits([self.prod_min_intvals[k], self.prod_max_intvals[k]])

    def set_out_format(self):
        self.out_min_intval = sum(self.prod_min_intvals)
        self.out_max_intval = sum(self.prod_max_intvals)
        self.out_fmt_width = Signed.get_bits([self.out_min_intval, self.out_max_intval])
        self.out_fmt = FixedSigned(n=self.out_fmt_width, point=self.out_fmt_point)

def create_pwl_repr(wave, addr_bits, t_start_intval, t_stop_intval, time_fmt):
    # calculate table step size
    n_seg = 1 << addr_bits
    addr_point = int(floor(time_fmt.point - log2((t_stop_intval - t_start_intval + 1) / (n_seg - 1))))
    addr_fmt = FixedUnsigned(n=addr_bits, point=addr_point)

    # calculate the start time of the segment
    addr_offset_intval = t_start_intval >> (time_fmt.point - addr_fmt.point)

    # make sure that the calculations are correct
    assert time_fmt.point >= addr_fmt.point
    int_fact = 1 << (time_fmt.point - addr_fmt.point)
    assert t_start_intval >= addr_offset_intval * int_fact
    assert t_stop_intval <= (addr_offset_intval + n_seg) * int_fact - 1

    # calculate a list of times for the segment start times
    times = (addr_offset_intval + np.arange(n_seg)) * addr_fmt.res

    # build pwl table
    pwl = wave.make_pwl(times=times)
    return PwlTable(pwl=pwl, addr_fmt=addr_fmt, addr_offset_intval=addr_offset_intval)

def find_pwl_repr(wave, t_start_intval, t_stop_intval, time_fmt, error_budget, addr_bits_max=14):
    # loop over the number of address bits
    addr_bits = 1

    while addr_bits <= addr_bits_max:
        pwl_table = create_pwl_repr(wave=wave, addr_bits=addr_bits, t_start_intval=t_start_intval,
                                    t_stop_intval=t_stop_intval, time_fmt=time_fmt)

        if pwl_table.pwl.error <= error_budget.err_pwl:
            return pwl_table

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

if __name__=='__main__':
    main()
