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
from msemu.verilog import VerilogPackage, VerilogConstant, VerilogTypedef

class ErrorBudget:
    # all errors are normalized to a particular value:
    # R_in: normalized to R_in
    # R_out : normalized to R_out
    # yss: normalized to yss
    # R_in*yss: normalized to R_in*yss

    def __init__(self,
                 in_ = 1e-3,            # error in input quantization [R_in]
                 trunc = 1e-2,          # residual settling error [yss]
                 pwl = 1e-3,            # error in pwl segment representation [yss]
                 step = 1e-3,           # error in step quantization [yss]
                 prod = 1e-3            # error in product of pulse response and input quantization [R_in*yss]
    ):
        self.trunc = trunc
        self.pwl = pwl
        self.step = step
        self.prod = prod
        self.in_ = in_

def main(db=-4, plot_dt=1e-12):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    err = ErrorBudget()
    emu = Emulation(db=db, err=err)

    emu.write_packages()
    emu.write_rom_files()

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
                 Tstop = 20e-9, # stopping time of emulation
                 Fnom = 8e9, # nominal TX frequency
                 jitter_pkpk = 10e-12, # peak-to-peak jitter of TX
                 R_in = 1, # input range
                 t_res = 1e-14 # smallest time resolution represented
    ):
        self.err = err
        self.db = db
        self.Tstop = Tstop
        self.Fnom = Fnom
        self.jitter_pkpk = jitter_pkpk
        self.R_in = R_in
        self.t_res = t_res

        # Get the step response
        self.compute_step()

        # Compute time format
        self.set_time_format()

        # Determine clock representation
        self.clk_tx = ClockWithJitter(freq=self.Fnom, jitter_pkpk=self.jitter_pkpk, time_fmt=self.time_fmt)
        self.clk_rx = ClockWithJitter(freq=self.Fnom, jitter_pkpk=self.jitter_pkpk, time_fmt=self.time_fmt, phases=2)

        # Set points of several signals
        self.set_in_format()
        self.set_filter_points()

        # Determine the number of UIs
        self.set_num_ui()

        # Build up a list of filter blocks
        self.create_filter_pwl_tables()

        # Set the widths of several signals
        self.set_filter_widths()

        # create verilog packages
        self.create_filter_package()
        self.create_time_package()
        self.create_signal_package()

    def compute_step(self):
        # Compute step response of channel and CTLE
        self.step = get_combined_step(db=self.db)

        # Find time at which step response has settled
        self.settled_time = self.step.find_settled_time(thresh=self.err.trunc)

    def set_time_format(self):
        # the following are full formats, with associated widths
        self.time_fmt = Fixed.make(self.Tstop, self.t_res, Unsigned)

    def set_in_format(self):
        # the following are full formats, with associated widths
        self.in_fmt = Fixed.make([-self.R_in, self.R_in], self.err.in_*self.R_in, Signed)

    def set_filter_points(self):
        self.step_point_fmt = PointFormat.make(self.err.step*self.step.yss)
        self.prod_point_fmt = PointFormat.make(self.err.prod*self.step.yss*self.R_in)

    def set_filter_widths(self):
        # bound the step responses
        filter_pwl_out_fmts = [filter_pwl_table.out_fmt for filter_pwl_table in self.filter_pwl_tables]
        self.step_fmt = max(filter_pwl_out_fmts, key = lambda out_fmt: out_fmt.n)

        # set the pulse format
        self.pulse_fmt = self.step_fmt - self.step_fmt

        # set the product format
        self.prod_fmt = (self.pulse_fmt * self.in_fmt).align_to(self.prod_point_fmt.point)

        # set the output format
        self.out_fmt = Fixed(point_fmt=self.prod_fmt,
                             width_fmt=Signed.make([self.num_ui*self.prod_fmt.min_int,
                                                    self.num_ui*self.prod_fmt.max_int]))

    def set_num_ui(self):
        # Determine number of UIs required to ensure the full step response is covered
        self.num_ui = int(ceil(self.settled_time / self.clk_tx.T_min_float)) + 1
        assert (self.num_ui-1)*self.clk_tx.T_min_float >= self.settled_time
        assert (self.num_ui-2)*self.clk_tx.T_min_float < self.settled_time

        # Set the format for the time history in the filter
        dt_max_int = self.num_ui * self.clk_tx.T_max_int
        self.dt_fmt = Fixed(point_fmt=self.time_fmt.point_fmt, width_fmt=Unsigned.make(dt_max_int))

    def create_filter_pwl_tables(self):
        self.filter_rom_names = []
        self.filter_pwl_tables = []
        for k in range(self.num_ui):
            filter_pwl_table = self.create_filter_pwl_table(k)
            self.filter_rom_names.append('filter_rom_'+str(k))
            self.filter_pwl_tables.append(filter_pwl_table)

    def create_filter_pwl_table(self, k, addr_bits_max=14):
        # compute range of times at which PWL table will be evaluated
        dt_start_int = k*self.clk_tx.T_min_int
        dt_stop_int = (k+1)*self.clk_tx.T_max_int

        # compute number of bits going into the PWL, after subtracting off dt_start_int
        pwl_time_bits = Unsigned.width(dt_stop_int - dt_start_int)

        # set tolerance for approximation by pwl segments
        pwl_tol = self.err.pwl * self.step.yss

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

            if pwl.error <= pwl_tol:
                return PwlTable(pwl=pwl,
                                high_bits_fmt = high_bits_fmt,
                                low_bits_fmt = low_bits_fmt,
                                addr_offset_int = dt_start_int,
                                offset_point_fmt = self.step_point_fmt,
                                slope_point_fmt = PointFormat.make(self.err.step / low_bits_fmt.max_float))

            rom_addr_bits += 1
        else:
            raise Exception('Failed to find a suitable PWL representation.')

    def write_filter_rom_files(self, dir='roms', suffix='.mem'):
        for filter_rom_name, filter_pwl_table in zip(self.filter_rom_names, self.filter_pwl_tables):
            filter_pwl_table.write_table(os.path.join(dir, filter_rom_name+suffix))

    def create_filter_package(self, name='filter_package'):
        pack = VerilogPackage(name=name)

        # number of UI
        pack.add(VerilogConstant(name='NUM_UI', value=self.num_ui, kind='int'))

        # add value formats
        pack.add_fixed_format(self.step_fmt, 'FILTER_STEP')
        pack.add_fixed_format(self.pulse_fmt, 'FILTER_PULSE')
        pack.add_fixed_format(self.prod_fmt, 'FILTER_PROD')

        # PWL-specific definitions
        pack.add(VerilogConstant(name='FILTER_ROM_NAMES', value=self.filter_rom_names, kind='string'))
        pack.add(VerilogConstant(name='FILTER_ADDR_WIDTHS',
                                 value=[filter_pwl_table.high_bits_fmt.n for filter_pwl_table in self.filter_pwl_tables],
                                 kind='int'))
        pack.add(VerilogConstant(name='FILTER_ADDR_OFFSETS',
                                 value=[filter_pwl_table.addr_offset_int for filter_pwl_table in self.filter_pwl_tables],
                                 kind='int'))
        pack.add(VerilogConstant(name='FILTER_SEGMENT_WIDTHS',
                                 value=[filter_pwl_table.low_bits_fmt.n for filter_pwl_table in self.filter_pwl_tables],
                                 kind='int'))
        pack.add(VerilogConstant(name='FILTER_OFFSET_WIDTHS',
                                 value=[filter_pwl_table.offset_fmt.n for filter_pwl_table in self.filter_pwl_tables],
                                 kind='int'))
        pack.add(VerilogConstant(name='FILTER_BIAS_VALS',
                                 value=[filter_pwl_table.bias_int for filter_pwl_table in self.filter_pwl_tables],
                                 kind='int'))
        pack.add(VerilogConstant(name='FILTER_SLOPE_WIDTHS',
                                 value=[filter_pwl_table.slope_fmt.n for filter_pwl_table in self.filter_pwl_tables],
                                 kind='int'))
        pack.add(VerilogConstant(name='FILTER_SLOPE_POINTS',
                                 value=[filter_pwl_table.slope_fmt.point for filter_pwl_table in self.filter_pwl_tables],
                                 kind='int'))

        self.filter_package = pack

    def create_time_package(self, name='time_package'):
        pack = VerilogPackage(name=name)

        # add time formats
        pack.add_fixed_format(self.time_fmt, 'TIME')
        pack.add_fixed_format(self.dt_fmt, 'DT')

        pack.add(VerilogConstant(name='TX_INC', value=self.clk_tx.T_nom_int, kind='longint'))
        pack.add(VerilogConstant(name='RX_INC', value=self.clk_rx.T_nom_int, kind='longint'))

        self.time_package = pack

    def create_signal_package(self, name='signal_package'):
        pack = VerilogPackage(name=name)

        pack.add_fixed_format(self.in_fmt, 'FILTER_IN')
        pack.add_fixed_format(self.out_fmt, 'FILTER_OUT')

        self.signal_package = pack

    def write_packages(self):
        self.filter_package.write_to_file()
        self.time_package.write_to_file()
        self.signal_package.write_to_file()

    def write_rom_files(self):
        self.write_filter_rom_files()

class PwlTable:
    def __init__(self, pwl, high_bits_fmt, low_bits_fmt, addr_offset_int, offset_point_fmt, slope_point_fmt):
        # save settings
        self.pwl = pwl
        self.high_bits_fmt = high_bits_fmt
        self.low_bits_fmt = low_bits_fmt
        self.addr_offset_int = addr_offset_int
        self.offset_point_fmt = offset_point_fmt
        self.slope_point_fmt = slope_point_fmt

        # check input validity
        assert np.isclose(self.high_bits_fmt.res, self.pwl.dtau)

        # set up the format of the ROM
        self.set_rom_fmt()

    def set_rom_fmt(self):
        # determine the bias
        bias_float = (min(self.pwl.offsets)+max(self.pwl.offsets))/2
        self.bias_int = self.offset_point_fmt.intval(bias_float)
        self.bias_fmt = Fixed(point_fmt=self.offset_point_fmt,
                              width_fmt=Signed.make(self.bias_int))

        # determine offset representation
        offset_floats = [offset - bias_float for offset in self.pwl.offsets]
        self.offset_ints = [self.offset_point_fmt.intval(offset_float) for offset_float in offset_floats]
        self.offset_fmt = Fixed(point_fmt=self.offset_point_fmt,
                                width_fmt=Signed.make(self.offset_ints))

        # determine slope representation
        self.slope_ints = [self.slope_point_fmt.intval(slope) for slope in self.pwl.slopes]
        self.slope_fmt = Fixed(point_fmt=self.slope_point_fmt,
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
                + (self.slope_fmt*self.low_bits_fmt.to_signed()).align_to(self.offset_point_fmt.point))

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

def get_combined_step(db=-4, dt=1e-12, T=20e-9):
    s4p = get_sample_s4p()
    t, imp_ch = s4p_to_impulse(s4p, dt, T)
    _, imp_ctle = get_ctle_imp(dt, T, db=db)
    imp_eff = fftconvolve(imp_ch, imp_ctle)[:len(t)]*dt
    step_eff = imp2step(imp=imp_eff, dt=dt)

    return Waveform(t=t, v=step_eff)

if __name__=='__main__':
    main()
