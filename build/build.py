import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import fftconvolve
from math import ceil, floor, log2
import logging, sys
import os.path
import pathlib
import collections

from msemu.rf import get_sample_s4p, s4p_to_impulse, imp2step
from msemu.pwl import Waveform
from msemu.fixed import Fixed, PointFormat, WidthFormat
from msemu.ctle import get_ctle_imp
from msemu.verilog import VerilogPackage, VerilogConstant
from msemu.tx_ffe import TxFFE

class ErrorBudget:
    # all errors are normalized to a particular value:
    # R_in: normalized to R_in
    # R_out : normalized to R_out
    # yss: normalized to yss
    # R_in*yss: normalized to R_in*yss

    def __init__(self,
                 in_ = 1e-4,            # error in input quantization [R_in]
                 pwl = 1e-3,            # error in pwl segment representation [yss]
                 step = 1e-4,           # error in step quantization [yss]
                 prod = 1e-4            # error in product of pulse response and input quantization [R_in*yss]
    ):
        self.pwl = pwl
        self.step = step
        self.prod = prod
        self.in_ = in_

def main(plot_dt=1e-12):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    err = ErrorBudget()
    emu = Emulation(err=err)

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
    seg_per_pulse = np.array([filter_pwl_table.n_segments for filter_pwl_table in emu.filter_pwl_tables])
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

    # Plot first step response
    for k, step in enumerate(emu.steps):
        plt.plot(step.t, step.v)

        for filter_pwl_table in emu.filter_pwl_tables:
            pwl = filter_pwl_table.pwls[k]
            t_eval = pwl.domain(plot_dt)
            plt.plot(t_eval, pwl.eval(t_eval))

        plt.xlabel('Time')
        plt.ylabel('Value')
        plt.savefig('step_resp_{}.pdf'.format(k))
        plt.clf()

class Emulation:
    def __init__(self,
                 err,                           # error budget
                 t_stop = 20e-9,                # stopping time of emulation
                 f_nom = 8e9,                   # nominal TX frequency
                 jitter_pkpk = 10e-12,          # peak-to-peak jitter of TX
                 t_res = 1e-14,                 # smallest time resolution represented
                 t_trunc = 10e-9                # time at which step response is truncated
    ):
        # save settings
        self.err = err
        self.t_stop = t_stop
        self.f_nom = f_nom
        self.jitter_pkpk = jitter_pkpk
        self.t_res = t_res
        self.t_trunc = t_trunc

        # Get the step responses and record the minimum steady-state value,
        # which sets precision requirements throughout the design
        self.steps = get_combined_step([-4])
        self.yss = min(step.yss for step in self.steps)

        # Compute time format
        self.set_time_format()

        # Determine clock representation
        self.create_clocks()

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
        self.create_packages()

    def set_time_format(self):
        # the following are full formats, with associated widths
        self.time_fmt = Fixed.make([0, self.t_stop], self.t_res, signed=False)

    def create_clocks(self):
        self.clk_tx = ClockWithJitter(freq=self.f_nom, jitter_pkpk=self.jitter_pkpk, time_fmt=self.time_fmt)
        self.clk_rx = ClockWithJitter(freq=self.f_nom, jitter_pkpk=self.jitter_pkpk, time_fmt=self.time_fmt, phases=2)

    def set_in_format(self):
        self.tx_ffe = TxFFE()

        # compute input point format
        self.R_in = max(sum(abs(tap) for tap in taps) for taps in self.tx_ffe.taps_array)
        self.in_point_fmt = PointFormat.make(self.err.in_*self.R_in)

        # compute tap representations
        format_tap_pair = lambda tap_pair: self.in_point_fmt.to_fixed(tap_pair, signed=True)
        format_setting = lambda setting: list(map(format_tap_pair, setting))
        setting_fmts = list(map(format_setting, self.tx_ffe.settings))

        # define the input format
        self.in_fmt = Fixed.cover(sum(setting_fmt) for setting_fmt in setting_fmts)

        # define the tap format
        self.tap_fmt = Fixed.cover(Fixed.cover(setting_fmt) for setting_fmt in setting_fmts)

        # log the results
        logging.debug('TX tap range: {} to {}'.format(self.tap_fmt.min_float, self.tap_fmt.max_float))
        logging.debug('Input range: {} to {}'.format(self.in_fmt.min_float, self.in_fmt.max_float))

    def set_filter_points(self):
        self.step_point_fmt = PointFormat.make(self.err.step*self.yss)
        self.prod_point_fmt = PointFormat.make(self.err.prod*self.yss*self.R_in)

    def set_filter_widths(self):
        # bound the step responses
        step_fmts = [filter_pwl_table.out_fmt for filter_pwl_table in self.filter_pwl_tables]
        self.step_fmt = Fixed.cover(step_fmts)

        # set the pulse format
        pulse_fmts = []
        for k, step_fmt in enumerate(step_fmts):
            if k==0:
                pulse_fmts.append(step_fmt)
            else:
                pulse_fmts.append(step_fmt - step_fmts[k-1])
        self.pulse_fmt = Fixed.cover(pulse_fmts)

        # set the product format
        self.prod_fmts = [(pulse_fmt * self.in_fmt).align_to(self.prod_point_fmt.point)
                          for pulse_fmt in pulse_fmts]
        self.prod_fmt = Fixed.cover(self.prod_fmts)

        # set the output format
        self.out_fmt = sum(self.prod_fmts)

        # print results for debugging
        logging.debug('Step range: {} to {}'.format(self.step_fmt.min_float, self.step_fmt.max_float))
        logging.debug('Pulse range: {} to {}'.format(self.pulse_fmt.min_float, self.pulse_fmt.max_float))
        logging.debug('Product range: {} to {}'.format(self.prod_fmt.min_float, self.prod_fmt.max_float))
        logging.debug('Output range: {} to {}'.format(self.out_fmt.min_float, self.out_fmt.max_float))

    def set_num_ui(self):
        # Determine number of UIs required to ensure the full step response is covered
        self.num_ui = int(ceil(self.t_trunc / self.clk_tx.T_min_float)) + 1
        assert (self.num_ui-1)*self.clk_tx.T_min_float >= self.t_trunc
        assert (self.num_ui-2)*self.clk_tx.T_min_float < self.t_trunc

        logging.debug('Number of UIs: {}'.format(self.num_ui))

        # Set the format for the time history in the filter
        dt_max_int = self.num_ui * self.clk_tx.T_max_int
        self.dt_fmt = Fixed(point_fmt=self.time_fmt.point_fmt,
                            width_fmt=WidthFormat.make([0, dt_max_int], signed=False))

    def create_filter_pwl_tables(self, rom_dir='roms'):
        # create rom directory if necessary
        this_file = os.path.abspath(__file__)
        self.rom_dir_path = os.path.abspath(os.path.join(os.path.dirname(this_file), rom_dir))
        pathlib.Path(self.rom_dir_path).mkdir(parents=True, exist_ok=True)

        self.filter_rom_paths = []
        self.filter_pwl_tables = []
        for k in range(self.num_ui):
            logging.debug('Building PWL #{}'.format(k))
            filter_pwl_table = self.create_filter_pwl_table(k)
            filter_rom_file = 'filter_rom_'+str(k)+'.mem'
            self.filter_rom_paths.append(os.path.join(self.rom_dir_path, filter_rom_file))
            self.filter_pwl_tables.append(filter_pwl_table)

    def create_filter_pwl_table(self, k, addr_bits_max=18):
        # compute range of times at which PWL table will be evaluated
        dt_start_int = k*self.clk_tx.T_min_int
        dt_stop_int = (k+1)*self.clk_tx.T_max_int

        # compute number of bits going into the PWL, after subtracting off dt_start_int
        pwl_time_bits = WidthFormat.width(dt_stop_int - dt_start_int, signed=False)

        # set tolerance for approximation by pwl segments
        pwl_tol = self.err.pwl * self.yss

        # iterate over the number of ROM address bits
        rom_addr_bits = 1
        while (rom_addr_bits <= addr_bits_max) and (rom_addr_bits < pwl_time_bits):
            # compute the pwl addr format
            high_bits_fmt = Fixed(width_fmt=WidthFormat(rom_addr_bits, signed=False),
                                  point_fmt=PointFormat(self.time_fmt.point - (pwl_time_bits - rom_addr_bits)))
            low_bits_fmt = Fixed(width_fmt=WidthFormat(pwl_time_bits-rom_addr_bits, signed=False),
                                 point_fmt=self.time_fmt.point_fmt)

            # calculate a list of times for the segment start times
            times = dt_start_int*self.time_fmt.res + (np.arange(high_bits_fmt.width_fmt.max+1)*high_bits_fmt.res)

            # build pwl table
            pwls = [step.make_pwl(times=times) for step in self.steps]

            if all(pwl.error <= pwl_tol for pwl in pwls):
                return PwlTable(pwls=pwls,
                                high_bits_fmt = high_bits_fmt,
                                low_bits_fmt = low_bits_fmt,
                                addr_offset_int = dt_start_int,
                                offset_point_fmt = self.step_point_fmt,
                                slope_point_fmt = PointFormat.make(self.err.step / low_bits_fmt.max_float))

            rom_addr_bits += 1
        else:
            raise Exception('Failed to find a suitable PWL representation.')

    def write_filter_rom_files(self, dir='roms'):
        for filter_rom_path, filter_pwl_table in zip(self.filter_rom_paths, self.filter_pwl_tables):
            filter_pwl_table.write_table(os.path.join(dir, filter_rom_path))

    def create_filter_package(self, name='filter_package'):
        pack = VerilogPackage(name=name)

        # number of UI
        pack.add(VerilogConstant(name='NUM_UI', value=self.num_ui, kind='int'))

        # RX CTLE settings
        pack.add(VerilogConstant(name='NUM_RX_SETTINGS', value=len(self.steps), kind='int'))
        pack.add(VerilogConstant(name='RX_SETTING_WIDTH',
                                 value=int(ceil(log2(len(self.steps)))),
                                 kind='int'))

        # add value formats
        pack.add_fixed_format(self.step_fmt, 'FILTER_STEP')
        pack.add_fixed_format(self.pulse_fmt, 'FILTER_PULSE')
        pack.add_fixed_format(self.prod_fmt, 'FILTER_PROD')
        pack.add(VerilogConstant(name='FILTER_PROD_WIDTHS',
                                 value=[prod_fmt.n for prod_fmt in self.prod_fmts],
                                 kind='int'))

        # PWL-specific definitions
        pack.add(VerilogConstant(name='FILTER_ROM_PATHS', value=self.filter_rom_paths, kind='string'))
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
                                 value=[filter_pwl_table.bias_ints for filter_pwl_table in self.filter_pwl_tables],
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
        pack.add(VerilogConstant(name='TIME_STOP', value=self.time_fmt.intval(self.t_stop), kind='longint'))

        self.time_package = pack

    def create_signal_package(self, name='signal_package'):
        pack = VerilogPackage(name=name)

        pack.add_fixed_format(self.in_fmt, 'FILTER_IN')
        pack.add_fixed_format(self.out_fmt, 'FILTER_OUT')

        self.signal_package = pack

    def create_tx_package(self, name='tx_package'):
        pack = VerilogPackage(name=name)

        pack.add_fixed_format(self.tap_fmt, 'TAP')
        pack.add(VerilogConstant(name='N_SETTINGS', value=self.tx_ffe.n_settings, kind='int'))
        pack.add(VerilogConstant(name='N_TAPS', value=self.tx_ffe.n_taps, kind='int'))

        # compute tx taps as integers
        tx_tap_intvals_plus = [[self.tap_fmt.intval(tap) for tap in taps] for taps in self.tx_ffe.taps_array]
        tx_tap_intvals_minus = [[self.tap_fmt.intval(-tap) for tap in taps] for taps in self.tx_ffe.taps_array]

        # add them to the package
        pack.add(VerilogConstant(name='TX_TAPS_PLUS', value=tx_tap_intvals_plus, kind='longint'))
        pack.add(VerilogConstant(name='TX_TAPS_MINUS', value=tx_tap_intvals_minus, kind='longint'))

        self.tx_package = pack

    def create_packages(self):
        self.create_filter_package()
        self.create_time_package()
        self.create_signal_package()
        self.create_tx_package()

    def write_packages(self):
        self.filter_package.write_to_file()
        self.time_package.write_to_file()
        self.signal_package.write_to_file()
        self.tx_package.write_to_file()

    def write_rom_files(self):
        self.write_filter_rom_files()

class PwlTable:
    def __init__(self, pwls, high_bits_fmt, low_bits_fmt, addr_offset_int, offset_point_fmt, slope_point_fmt):
        # save settings
        self.pwls = pwls
        self.high_bits_fmt = high_bits_fmt
        self.low_bits_fmt = low_bits_fmt
        self.addr_offset_int = addr_offset_int
        self.offset_point_fmt = offset_point_fmt
        self.slope_point_fmt = slope_point_fmt

        # check input validity
        assert all(np.isclose(pwl.dtau, self.high_bits_fmt.res) for pwl in self.pwls)

        # set up the format of the ROM
        self.set_rom_fmt()

    @property
    def n_segments(self):
        n_segments_0 = self.pwls[0].n
        assert all(pwl.n == n_segments_0 for pwl in self.pwls)
        return n_segments_0

    @property
    def n_settings(self):
        return len(self.pwls)

    def set_rom_fmt(self):
        # determine the bias
        bias_floats = [min(pwl.offsets)+max(pwl.offsets)/2 for pwl in self.pwls]
        self.bias_ints = self.offset_point_fmt.intval(bias_floats)
        bias_fmts = [Fixed(point_fmt=self.offset_point_fmt,
                           width_fmt=WidthFormat.make(bias_int, signed=True))
                     for bias_int in self.bias_ints]
        self.bias_fmt = Fixed.cover(bias_fmts)

        # determine offset representation
        offset_floats = [[offset - bias_float for offset in pwl.offsets]
                         for pwl, bias_float in zip(self.pwls, bias_floats)]
        self.offset_ints = [self.offset_point_fmt.intval(setting)
                            for setting in offset_floats]
        offset_fmts = [[Fixed(point_fmt=self.offset_point_fmt,
                              width_fmt=WidthFormat.make(offset_int, signed=True))
                        for offset_int in setting]
                       for setting in self.offset_ints]
        self.offset_fmt = Fixed.cover(Fixed.cover(setting) for setting in offset_fmts)

        # determine slope representation
        self.slope_ints = [self.slope_point_fmt.intval(pwl.slopes)
                           for pwl in self.pwls]
        slope_fmts = [[Fixed(point_fmt=self.slope_point_fmt,
                             width_fmt=WidthFormat.make(slope_int, signed=True))
                       for slope_int in setting]
                      for setting in self.slope_ints]
        self.slope_fmt = Fixed.cover(Fixed.cover(setting) for setting in slope_fmts)

        # determine output representation of output
        out_fmts = []

        for setting in range(self.n_settings):
            for offset_fmt, slope_fmt in zip(offset_fmts[setting],
                                             slope_fmts[setting]):
                out_fmts.append(bias_fmts[setting]
                                + offset_fmt
                                + (slope_fmt * self.low_bits_fmt.to_signed()).align_to(self.offset_point_fmt.point))

        self.out_fmt = Fixed.cover(out_fmts)

    def write_table(self, fname):
        with open(fname, 'w') as f:
            for setting in range(self.n_settings):
                for offset_str, slope_str in zip(self.offset_fmt.width_fmt.bin_str(self.offset_ints[setting]),
                                                 self.slope_fmt.width_fmt.bin_str(self.slope_ints[setting])):
                    f.write(offset_str+slope_str+'\n')

    @property
    def table_size_bits(self):
        return self.n_settings * self.n_segments * (self.offset_fmt.n + self.slope_fmt.n)

class ClockWithJitter:
    def __init__(self, freq, jitter_pkpk, time_fmt, phases=1):
        # save time format
        self.time_fmt = time_fmt

        # compute jitter format
        # it is set up so that the min and max values are the absolute min and max possible in the representation,
        # since a PRBS will be used to generate them
        jitter_min_int = time_fmt.point_fmt.intval(-jitter_pkpk/2, floor)
        jitter_max_int = time_fmt.point_fmt.intval(jitter_pkpk/2, ceil)
        jitter_width = max(WidthFormat.width([jitter_min_int, jitter_max_int], signed=True))
        self.jitter_fmt = Fixed(point_fmt=self.time_fmt.point_fmt,
                                width_fmt=WidthFormat(jitter_width, signed=True))

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

def get_combined_step(db_val_or_vals=-4, dt=0.1e-12, T=20e-9):
    if isinstance(db_val_or_vals, collections.Iterable):
        db_vals = db_val_or_vals
    else:
        db_vals = [db_val_or_vals]

    # get channel impulse response
    s4p = get_sample_s4p()
    t, imp_ch = s4p_to_impulse(s4p, dt, T)

    # generate all of the requested step responses
    steps = []
    for db_val in db_vals:
        logging.debug('Generating impulse response with dB={:.1f}'.format(db_val))

        # get ctle impulse response for this db value
        _, imp_ctle = get_ctle_imp(dt, T, db=db_val)

        # compute combined impulse response
        imp_eff = fftconvolve(imp_ch, imp_ctle)[:len(t)]*dt

        # compute resulting step response
        step = Waveform(t=t, v=imp2step(imp=imp_eff, dt=dt))

        # store the step response
        steps.append(step)

    if isinstance(db_val_or_vals, collections.Iterable):
        return steps
    else:
        return steps[0]

if __name__=='__main__':
    main()
