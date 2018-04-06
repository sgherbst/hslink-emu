import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import fftconvolve
from math import ceil, floor, log2
import logging, sys
import os.path

from msemu.rf import get_sample_s4p, s4p_to_impulse, imp2step
from msemu.pwl import Waveform
from msemu.fixed import Fixed, Signed, Unsigned, PointFormat
from msemu.ctle import get_ctle_imp
from msemu.verilog import VerilogPackage, DefineVariable, VerilogTypedef

class ErrorBudget:
    # all errors are normalized to a particular value:
    # R_in: normalized to R_in
    # R_out : normalized to R_out
    # yss: normalized to yss
    # R_in*yss: normalized to R_in*yss

    def __init__(self,
                 trunc = 1e-2, # residual settling error [yss]
                 step = 1e-3, # error in step representation [yss]
                 pulse = 1e-3, # error in pulse representation [yss]
                 prod = 1e-3, # error in product of pulse response and input [R_in*yss]
                 in_ = 1e-3, # error in representing the input [R_in]
                 out = 1e-3, # error in representing the output [R_out]
    ):
        self.trunc = trunc
        self.step = step
        self.pulse = pulse
        self.prod = prod
        self.in_ = in_
        self.out = out

def main(db=-4, plot_dt=1e-12):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    err = ErrorBudget()
    emu = Emulation(db=db, err=err)

    # emu.write_filter_rom_files()
    # emu.write_filter_package()
    #
    # emu.write_time_package()
    # emu.write_signal_package()

    # Plot bits used for PWL ROMs
    bits_per_pulse = np.array([filter_pwl_table.table_size_bits for filter_pwl_table in emu.filter_pwl_tables])
    plt.plot(bits_per_pulse)
    plt.xlabel('Step Response #')
    plt.ylabel('ROM Bits')
    plt.savefig('rom_bits.pdf')
    plt.clf()

    # Plot number of segments for PWLs
    seg_per_pulse = np.array([filter_pwl_table.pwl.n for filter_pwl_table in emu.filter_pwl_tables])
    plt.plot(seg_per_pulse)
    plt.xlabel('Step Response #')
    plt.ylabel('PWL Segments')
    plt.savefig('pwl_segments.pdf')
    plt.clf()

    # Plot number of segments for PWLs
    data_width_per_pulse = np.array([filter_pwl_table.offset_fmt.n+filter_pwl_table.slope_fmt.n for filter_pwl_table in emu.filter_pwl_tables])
    plt.plot(data_width_per_pulse)
    plt.xlabel('Step Response #')
    plt.ylabel('Data Width')
    plt.savefig('pwl_data_width.pdf')
    plt.clf()

    # Plot step response
    plt.plot(emu.step.t, emu.step.v)

    for filter_pwl_table in emu.filter_pwl_tables:
        pwl = filter_pwl_table.pwl
        t_eval = pwl.domain(plot_dt)
        plt.plot(t_eval, pwl.eval(t_eval))
    plt.xlabel('Time')
    plt.ylabel('Value')
    plt.savefig('step_resp.pdf')
    plt.clf()

class Emulation:
    def __init__(self,
                 err, # error budget
                 db = -4, # CTLE gain setting
                 Tstop = 4e-9, # stopping time of emulation
                 Fnom = 8e9, # nominal TX frequency
                 jitter_pkpk = 10e-12, # peak-to-peak jitter of TX
                 R_in = 1, # input range
                 R_out = 1, # output range
                 t_res = 1e-14 # smallest time resolution represented
    ):
        self.err = err
        self.db = db
        self.Tstop = Tstop
        self.Fnom = Fnom
        self.jitter_pkpk = jitter_pkpk
        self.R_in = R_in
        self.R_out = R_out
        self.t_res = t_res

        # Get the step response
        self.compute_step()

        # Compute time format
        self.set_time_format()

        # Determine clock representation
        self.clk_tx = ClockWithJitter(freq=self.Fnom, jitter_pkpk=self.jitter_pkpk, time_fmt=self.time_fmt)
        self.clk_rx = ClockWithJitter(freq=self.Fnom, jitter_pkpk=self.jitter_pkpk, time_fmt=self.time_fmt, phases=2)

        # Set points of several signals
        self.set_io_formats()
        self.set_common_points()

        # Determine the number of UIs
        self.set_num_ui()

        # Build up a list of filter blocks
        self.create_filter_pwl_tables()

        # Set the widths of several signals
        self.set_common_widths()

    def compute_step(self):
        # Compute step response of channel and CTLE
        self.step = get_combined_step(db=self.db)

        # Find time at which step response has settled
        self.settled_time = self.step.find_settled_time(thresh=self.err.trunc)

    def set_time_format(self):
        # the following are full formats, with associated widths
        self.time_fmt = Fixed.make(self.Tstop, self.t_res, Unsigned)

    def set_io_formats(self):
        # the following are full formats, with associated widths
        self.in_fmt = Fixed.make([-self.R_in, self.R_in], self.err.in_*self.R_in, Signed)
        self.out_fmt = Fixed.make([-self.R_out, self.R_out], self.err.out*self.R_out, Signed)

    def set_common_points(self):
        self.step_point_fmt = PointFormat.make(self.err.step*self.step.yss)
        self.pulse_point_fmt = PointFormat.make(self.err.pulse*self.step.yss)
        self.prod_point_fmt = PointFormat.make(self.err.prod*self.step.yss*self.R_in)

    def set_common_widths(self):
        # bound the step responses
        filter_pwl_out_fmts = [filter_pwl_table.out_fmt for filter_pwl_table in self.filter_pwl_tables]
        self.step_fmt = max(filter_pwl_out_fmts, key = lambda out_fmt: out_fmt.n)

        # bound the pulse responses
        self.pulse_fmt = self.step_fmt - self.step_fmt

        # bound the products
        self.prod_fmt = self.in_fmt * self.pulse_fmt

    def set_num_ui(self):
        # Determine number of UIs required to ensure the full step response is covered
        self.num_ui = int(ceil(self.settled_time / self.clk_tx.T_min_float)) + 1
        assert (self.num_ui-1)*self.clk_tx.T_min_float >= self.settled_time
        assert (self.num_ui-2)*self.clk_tx.T_min_float < self.settled_time

        # create a list of PWL tables to be used
        self.pwl_tables = [None]*self.num_ui

        # Set the format for the time history in the filter
        dt_max_int = self.num_ui * self.clk_tx.T_max_int
        self.dt_fmt = Fixed(point_fmt=self.time_fmt.point_fmt, width_fmt=Unsigned.make(dt_max_int))

    def create_filter_pwl_tables(self):
        self.filter_pwl_tables = []
        for k in range(self.num_ui):
            filter_pwl_table = self.create_filter_pwl_table(k)
            self.filter_pwl_tables.append(filter_pwl_table)

    def create_filter_pwl_table(self, k, addr_bits_max=14):
        # compute range of times at which PWL table will be evaluated
        dt_start_int = k*self.clk_tx.T_min_int
        dt_stop_int = (k+1)*self.clk_tx.T_max_int

        # compute number of bits going into the PWL, after subtracting off dt_start_int
        pwl_time_bits = Unsigned.width(dt_stop_int - dt_start_int)

        # set tolerance for loop
        tol = self.err.step * self.step.yss

        # iterate over the number of ROM address bits
        rom_addr_bits = 1
        while (rom_addr_bits <= addr_bits_max) and (rom_addr_bits < pwl_time_bits):
            # compute the pwl addr format
            high_bits_fmt = Fixed(width_fmt=Unsigned(rom_addr_bits),
                                  point_fmt=PointFormat(self.time_fmt.point - (pwl_time_bits - rom_addr_bits)))
            low_bits_fmt = Fixed(width_fmt=Unsigned(pwl_time_bits - rom_addr_bits),
                                 point_fmt=self.time_fmt.point_fmt)

            # calculate a list of times for the segment start times
            times = dt_start_int*self.time_fmt.res + (np.arange(high_bits_fmt.width_fmt.max+1)*high_bits_fmt.res)

            # build pwl table
            pwl = self.step.make_pwl(times=times)

            if pwl.error <= tol:
                return PwlTable(pwl=pwl, high_bits_fmt=high_bits_fmt, low_bits_fmt=low_bits_fmt,
                                addr_offset_int=dt_start_int, out_point_fmt=self.step_point_fmt, tol=tol)

            rom_addr_bits += 1
        else:
            raise Exception('Failed to find a suitable PWL representation.')

    def write_filter_rom_files(self, dir='roms', prefix='filter_rom_', suffix='.mem'):
        self.filter_rom_names = []
        for k, filter_pwl_table in enumerate(self.filter_pwl_tables):
            # generate name
            filter_rom_name = prefix + str(k) + suffix

            # write to file
            filter_pwl_table.write_table(os.path.join(dir, self.filter_rom_name))

            # keep track of names
            self.filter_rom_names.append(filter_rom_name)

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
    def __init__(self, pwl, high_bits_fmt, low_bits_fmt, addr_offset_int, out_point_fmt, tol):
        # save settings
        self.pwl = pwl
        self.high_bits_fmt = high_bits_fmt
        self.low_bits_fmt = low_bits_fmt
        self.addr_offset_int = addr_offset_int
        self.out_point_fmt = out_point_fmt
        self.tol = tol

        # check input validity
        assert np.isclose(self.high_bits_fmt.res, self.pwl.dtau)

        # set up the format of the ROM
        self.set_rom_fmt()

    def set_rom_fmt(self):
        # determine the bias
        bias_float = (min(self.pwl.offsets)+max(self.pwl.offsets))/2
        self.bias_int = self.out_point_fmt.intval(bias_float)
        self.bias_fmt = Fixed(point_fmt=self.out_point_fmt,
                              width_fmt=Signed.make(self.bias_int))

        # determine offset representation
        offset_floats = [offset - bias_float for offset in self.pwl.offsets]
        self.offset_ints = [self.out_point_fmt.intval(offset_float) for offset_float in offset_floats]
        self.offset_fmt = Fixed(point_fmt=self.out_point_fmt,
                                width_fmt=Signed.make(self.offset_ints))

        # determine slope representation
        slope_point_fmt = PointFormat.make(self.tol / self.low_bits_fmt.max_float)
        self.slope_ints = [slope_point_fmt.intval(slope) for slope in self.pwl.slopes]
        self.slope_fmt = Fixed(point_fmt=slope_point_fmt,
                               width_fmt=Signed.make(self.slope_ints))

    def to_table_str(self):
        retval = ''

        for offset_int, slope_int in zip(self.offset_ints, self.slope_ints):
            retval += self.offset_fmt.width_fmt.bin_str(offset_int)
            retval += self.slope_fmt.width_fmt.bin_str(slope_int)
            retval += '\n'

        return retval

    def write_table(self, fname):
        table_str = self.to_table_str()
        with open(fname, 'w') as f:
            f.write(table_str)

    @property
    def out_fmt(self):
        return (self.bias_fmt
                + self.offset_fmt
                + (self.slope_fmt*self.low_bits_fmt.signed()).align_to(self.out_point_fmt.point))

    @property
    def table_size_bits(self):
        return self.pwl.n * (self.offset_fmt.n + self.slope_fmt.n)

class ClockWithJitter:
    def __init__(self, freq, jitter_pkpk, time_fmt, phases=1):
        # save time format
        self.time_fmt = time_fmt

        # compute jitter format
        self.jitter_fmt = time_fmt.point_fmt.to_fixed([-jitter_pkpk/2, jitter_pkpk/2], Signed)

        # compute main time format
        self.T_nom_int = time_fmt.intval(1/(phases*freq))

        # make sure the jitter isn't too large
        assert self.T_nom_int + self.jitter_fmt.min_int > 0

    @property
    def T_nom_float(self):
        return self.T_nom_int * self.time_fmt.res

    @property
    def T_min_int(self):
        return self.T_nom_int + self.jitter_fmt.min_int

    @property
    def T_max_int(self):
        return self.T_nom_int + self.jitter_fmt.max_int

    @property
    def T_min_float(self):
        return self.T_min_int * self.time_fmt.res

    @property
    def T_max_float(self):
        return self.T_max_int * self.time_fmt.res

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


def get_combined_step(db=-4, dt=1e-12, T=20e-9):
    s4p = get_sample_s4p()
    t, imp_ch = s4p_to_impulse(s4p, dt, T)
    _, imp_ctle = get_ctle_imp(dt, T, db=db)
    imp_eff = fftconvolve(imp_ch, imp_ctle)[:len(t)]*dt
    step_eff = imp2step(imp=imp_eff, dt=dt)

    return Waveform(t=t, v=step_eff)

if __name__=='__main__':
    main()
