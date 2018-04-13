import matplotlib.pyplot as plt
import numpy as np
from math import ceil, floor, log2
import logging, sys
import os.path
import json

from msemu.fixed import Fixed, PointFormat, WidthFormat
from msemu.ctle import RxDynamics
from msemu.verilog import VerilogPackage, VerilogConstant
from msemu.tx_ffe import TxFFE
from msemu.cmd import get_parser, mkdir_p
from msemu.lfsr import LFSR
from msemu.clocks import TxClock, RxClock
from msemu.dfe import DFE

class ErrorBudget:
    # all errors are normalized to a particular value:
    # R_in: normalized to R_in
    # R_out : normalized to R_out
    # yss: normalized to yss
    # R_in*yss: normalized to R_in*yss

    def __init__(
        self,
        in_ = 1e-4,            # error in input quantization [R_in]
        pwl = 1e-3,            # error in pwl segment representation [yss]
        step = 1e-4,           # error in step quantization [yss]
        prod = 1e-4            # error in product of pulse response and input quantization [R_in*yss]
    ):
        self.pwl = pwl
        self.step = step
        self.prod = prod
        self.in_ = in_

class Emulation:
    def __init__(
        self,
        err,                           # error budget
        t_stop = 20e-9,                # stopping time of emulation
        f_rx_min = 7.5e9,              # minimum RX frequency
        f_rx_max = 8.5e9,              # maximum RX frequency
        f_rx_init = 7.95e9,            # initial RX frequency
        f_tx_nom = 8e9,                # nominal TX frequency
        dco_bits = 14,                 # number of DCO bits
        jitter_pkpk_tx = 10e-12,       # peak-to-peak jitter of TX
        jitter_pkpk_rx = 10e-12,       # peak-to-peak jitter of RX
        t_res = 1e-14,                 # smallest time resolution represented
        t_trunc = 10e-9,               # time at which step response is truncated
        n_dfe_taps = 2,                # number of dfe taps
        build_dir = '../build/',       # where packages are stored
        channel_dir = '../channel/',   # where channel data are stored
        data_dir = '../data/',         # where ADC data are stored
        rom_dir = '../build/roms',     # where ROM files are stored
        rom_ext = 'mem'                # file extension of ROMs
    ):
        # save emulation settings
        self.err = err
        self.t_stop = t_stop
        self.f_rx_min = f_rx_min
        self.f_rx_max = f_rx_max
        self.f_rx_init = f_rx_init
        self.f_tx_nom = f_tx_nom
        self.dco_bits = dco_bits
        self.jitter_pkpk_tx = jitter_pkpk_tx
        self.jitter_pkpk_rx = jitter_pkpk_rx
        self.t_res = t_res
        self.t_trunc = t_trunc
        self.n_dfe_taps = n_dfe_taps

        # store file output settings
        self.build_dir = os.path.abspath(build_dir)
        self.channel_dir = os.path.abspath(channel_dir)
        self.data_dir = os.path.abspath(data_dir)
        self.rom_dir = os.path.abspath(rom_dir)
        self.rom_ext = rom_ext
        
        # create directories if necessary
        mkdir_p(self.build_dir)
        mkdir_p(self.channel_dir)
        mkdir_p(self.data_dir)
        mkdir_p(self.rom_dir)

        # get the RX dynamics model
        self.rx_dyn = RxDynamics(dir_name=self.channel_dir)

        # Get the step responses and record the minimum steady-state value,
        # which sets precision requirements throughout the design
        self.steps = []
        for k in range(self.rx_dyn.n):
            step = self.rx_dyn.get_step(k)
            self.steps.append(step)
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

        # Set formatting associated with DFE
        self.set_dfe_formats()

        # create verilog packages
        self.tx_ffe_rom_name = 'tx_ffe_rom' + '.' + self.rom_ext
        self.create_packages()

        # write output
        self.write_packages()
        self.write_rom_files()
        self.write_formats()

    def set_time_format(self):
        # the following are full formats, with associated widths
        self.time_fmt = Fixed.make([0, self.t_stop], self.t_res, signed=False)

    def create_clocks(self):
        self.clk_tx = TxClock(freq=self.f_tx_nom, jitter_pkpk=self.jitter_pkpk_tx, time_fmt=self.time_fmt)
        self.clk_rx = RxClock(finit=self.f_rx_init, fmin=self.f_rx_min, fmax=self.f_rx_max, bits=self.dco_bits, jitter_pkpk=self.jitter_pkpk_rx, time_fmt=self.time_fmt)

    def set_in_format(self):
        self.tx_ffe = TxFFE()

        # Determine range of inputs
        self.R_in = max(max(abs(elem) for elem in setting) for setting in self.tx_ffe.settings)
        logging.debug('R_in = {}'.format(self.R_in))

        # compute input point format
        self.in_point_fmt = PointFormat.make(self.err.in_*self.R_in)

        # compute tap representations
        in_fmts = [Fixed(point_fmt=self.in_point_fmt,
                         width_fmt=WidthFormat.make(self.in_point_fmt.intval(setting), signed=True))
                   for setting in self.tx_ffe.settings]

        # define the input format
        self.in_fmt = Fixed.cover(in_fmts)

        # log the results
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

    def set_dfe_formats(self):
        # create DFE object
        ui = 1/self.f_tx_nom
        self.dfe = DFE(tx_ffe=self.tx_ffe,
                       rx_dyn=self.rx_dyn,
                       ui=ui,
                       n_taps=self.n_dfe_taps)

        # compute DFE tap representations
        dfe_out_fmts = []
        for tx_setting in range(self.tx_ffe.n_settings):
            for rx_setting in range(self.rx_dyn.n):
                setting = self.dfe.settings[tx_setting][rx_setting]

                point_fmt = self.out_fmt.point_fmt
                width_fmt = WidthFormat.make(point_fmt.intval(setting), signed=True)

                dfe_out_fmts.append(Fixed(point_fmt=point_fmt,
                                          width_fmt=width_fmt))

        # define DFE format to cover all values that need to be represented
        self.dfe_out_fmt = Fixed.cover(dfe_out_fmts)

        # define comparator input format
        self.comp_in_fmt = self.out_fmt + self.dfe_out_fmt

    def set_num_ui(self):
        # Determine number of UIs required to ensure the full step response is covered
        self.num_ui = int(ceil(self.t_trunc / self.clk_tx.out_fmt.min_float)) + 1
        assert (self.num_ui-1)*self.clk_tx.out_fmt.min_float >= self.t_trunc
        assert (self.num_ui-2)*self.clk_tx.out_fmt.min_float < self.t_trunc

        logging.debug('Number of UIs: {}'.format(self.num_ui))

        # Set the format for the time history in the filter
        dt_max_int = self.num_ui * self.clk_tx.out_fmt.max_int
        self.dt_fmt = Fixed(point_fmt=self.time_fmt.point_fmt,
                            width_fmt=WidthFormat.make([0, dt_max_int], signed=False))

    def create_filter_pwl_tables(self, filter_segment_prefix='filter_segment_rom',
                                 filter_bias_prefix='filter_bias_rom'):
        self.filter_segment_rom_names = []
        self.filter_bias_rom_names = []
        self.filter_pwl_tables = []
        for k in range(self.num_ui):
            logging.debug('Building PWL #{}'.format(k))
            filter_pwl_table = self.create_filter_pwl_table(k)
            filter_segment_rom_name = '{:s}_{:d}.{:s}'.format(filter_segment_prefix, k, self.rom_ext)
            filter_bias_rom_name = '{:s}_{:d}.{:s}'.format(filter_bias_prefix, k, self.rom_ext)
            self.filter_segment_rom_names.append(filter_segment_rom_name)
            self.filter_bias_rom_names.append(filter_bias_rom_name)
            self.filter_pwl_tables.append(filter_pwl_table)

    def create_filter_pwl_table(self, k, addr_bits_max=18):
        # compute range of times at which PWL table will be evaluated
        dt_start_int = k*self.clk_tx.out_fmt.min_int
        dt_stop_int = (k+1)*self.clk_tx.out_fmt.max_int

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

    def write_filter_rom_files(self):
        for (filter_pwl_table,
             filter_segment_rom_name,
             filter_bias_rom_name) in zip(self.filter_pwl_tables,
                                          self.filter_segment_rom_names,
                                          self.filter_bias_rom_names):
            filter_pwl_table.write_segment_table(os.path.join(self.rom_dir, filter_segment_rom_name))
            filter_pwl_table.write_bias_table(os.path.join(self.rom_dir, filter_bias_rom_name))

    def write_tx_ffe_rom_file(self):
        self.tx_ffe.write_table(file_name=os.path.join(self.rom_dir, self.tx_ffe_rom_name),
                                fixed_format=self.in_fmt)

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
        pack.add(VerilogConstant(name='FILTER_SEGMENT_ROM_NAMES', value=self.filter_segment_rom_names, kind='string'))
        pack.add(VerilogConstant(name='FILTER_BIAS_ROM_NAMES', value=self.filter_bias_rom_names, kind='string'))
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
        pack.add(VerilogConstant(name='FILTER_BIAS_WIDTHS',
                                 value=[filter_pwl_table.bias_fmt.n for filter_pwl_table in self.filter_pwl_tables],
                                 kind='longint'))
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

        # TX clock
        pack.add_fixed_format(self.clk_tx.jitter_fmt, 'TX_JITTER')
        pack.add_fixed_format(self.clk_tx.period_fmt, 'TX_PERIOD')
        pack.add(VerilogConstant(name='TX_PERIOD_VAL', value=self.clk_tx.T_nom_int, kind='longint'))

        # RX clock
        pack.add_fixed_format(self.clk_rx.jitter_fmt, 'RX_JITTER')
        pack.add_fixed_format(self.clk_rx.period_fmt, 'DCO_PERIOD')
        pack.add_fixed_format(self.clk_rx.code_fmt, 'DCO_CODE')
        pack.add_fixed_format(self.clk_rx.offset_fmt, 'DCO_OFFSET')
        pack.add_fixed_format(self.clk_rx.slope_fmt, 'DCO_SLOPE')
        pack.add_fixed_format(self.clk_rx.prod_fmt, 'DCO_PROD')
        pack.add(VerilogConstant(name='DCO_SLOPE_VAL', value=self.clk_rx.slope_int, kind='longint'))
        pack.add(VerilogConstant(name='DCO_OFFSET_VAL', value=self.clk_rx.offset_int, kind='longint'))
        pack.add(VerilogConstant(name='DCO_CODE_INIT', value=self.clk_rx.code_init, kind='longint'))

        # Stopping time
        pack.add(VerilogConstant(name='TIME_STOP', value=self.time_fmt.intval(self.t_stop), kind='longint'))

        self.time_package = pack

    def create_signal_package(self, name='signal_package'):
        pack = VerilogPackage(name=name)

        pack.add_fixed_format(self.in_fmt, 'FILTER_IN')
        pack.add_fixed_format(self.out_fmt, 'FILTER_OUT')

        self.signal_package = pack

    def create_tx_package(self, name='tx_package'):
        pack = VerilogPackage(name=name)

        pack.add(VerilogConstant(name='N_TX_SETTINGS', value=self.tx_ffe.n_settings, kind='int'))
        pack.add(VerilogConstant(name='TX_SETTING_WIDTH', value=self.tx_ffe.setting_width, kind='int'))
        pack.add(VerilogConstant(name='N_TX_TAPS', value=self.tx_ffe.n_taps, kind='int'))
        pack.add(VerilogConstant(name='TX_FFE_ROM_NAME', value=self.tx_ffe_rom_name, kind='string'))

        self.tx_package = pack

    def create_rx_package(self, name='rx_package'):
        pack = VerilogPackage(name=name)

        pack.add_fixed_format(self.dfe_out_fmt, 'DFE_OUT')
        pack.add_fixed_format(self.comp_in_fmt, 'COMP_IN')
        pack.add(VerilogConstant(name='N_DFE_TAPS', value=self.n_dfe_taps, kind='int'))

        self.rx_package = pack

    def create_path_package(self, name='path_package'):
        pack = VerilogPackage(name=name)

        pack.add(VerilogConstant(name='ROM_DIR', value=self.rom_dir, kind='string'))
        pack.add(VerilogConstant(name='DATA_DIR', value=self.data_dir, kind='string'))

        self.path_package = pack

    def create_lfsr_package(self, name='lfsr_package'):
        self.lfsr_package = LFSR().get_package(name=name)

    def create_packages(self):
        self.create_filter_package()
        self.create_time_package()
        self.create_signal_package()
        self.create_tx_package()
        self.create_path_package()
        self.create_lfsr_package()
        self.create_rx_package()

    def write_packages(self):
        self.filter_package.write(self.build_dir)
        self.time_package.write(self.build_dir)
        self.signal_package.write(self.build_dir)
        self.tx_package.write(self.build_dir)
        self.path_package.write(self.build_dir)
        self.lfsr_package.write(self.build_dir)
        self.rx_package.write(self.build_dir)

    def write_rom_files(self):
        self.write_filter_rom_files()
        self.write_tx_ffe_rom_file()

    def write_formats(self):
        fmt_dict = {
            'in_fmt': self.in_fmt.to_dict(),
            'out_fmt': self.out_fmt.to_dict(),
            'time_fmt': self.time_fmt.to_dict()
        }
        fmt_dict_str = json.dumps(fmt_dict, indent=2, sort_keys=True)
        fmt_dict_file = os.path.join(self.build_dir, 'fmt_dict.json')
        with open(fmt_dict_file, 'w') as f:
            f.write(fmt_dict_str)

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

    @property
    def setting_bits(self):
        return int(ceil(log2(self.n_settings)))

    @property
    def setting_padding(self):
        return ((1<<self.setting_bits)-self.n_settings)

    def set_rom_fmt(self):
        # determine the bias
        bias_floats = [(min(pwl.offsets)+max(pwl.offsets))/2 for pwl in self.pwls]
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

    def write_segment_table(self, fname):
        with open(fname, 'w') as f:
            # write the segment tables for each setting one after another
            for offset_setting, slope_setting in zip(self.offset_ints, self.slope_ints):
                offset_strs = self.offset_fmt.width_fmt.bin_str(offset_setting)
                slope_strs = self.slope_fmt.width_fmt.bin_str(slope_setting)
                for offset_str, slope_str in zip(offset_strs, slope_strs):
                    f.write(offset_str+slope_str+'\n')

            # pad the end with zeros as necessary
            zero_str = '0'*(self.offset_fmt.n+self.slope_fmt.n)
            for i in range(self.setting_padding):
                for j in range(self.n_segments):
                    f.write(zero_str+'\n')

    def write_bias_table(self, fname):
        with open(fname, 'w') as f:
            # write the bias values into a table
            for bias_str in self.bias_fmt.width_fmt.bin_str(self.bias_ints):
                f.write(bias_str + '\n')

            # pad the end with zeros as necessary
            zero_str = '0'*self.bias_fmt.n
            for i in range(self.setting_padding):
                f.write(zero_str+'\n')

    @property
    def table_size_bits(self):
        return self.n_settings * self.n_segments * (self.offset_fmt.n + self.slope_fmt.n)

def main(plot_dt=1e-12):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    err = ErrorBudget()
    emu = Emulation(err=err,
                    build_dir=args.build_dir,
                    channel_dir=args.channel_dir,
                    rom_dir=args.rom_dir,
                    data_dir=args.data_dir)

    # Produce output plots
    mkdir_p(args.data_dir)

    # Plot bits used for PWL ROMs
    bits_per_pulse = np.array([filter_pwl_table.table_size_bits for filter_pwl_table in emu.filter_pwl_tables])
    plt.plot(bits_per_pulse)
    plt.xlabel('Step Response #')
    plt.ylabel('ROM Bits')
    plt.savefig(os.path.join(args.data_dir, 'rom_bits.pdf'))
    plt.clf()

    # Plot number of segments for PWLs
    seg_per_pulse = np.array([filter_pwl_table.n_segments for filter_pwl_table in emu.filter_pwl_tables])
    plt.plot(seg_per_pulse)
    plt.xlabel('Step Response #')
    plt.ylabel('PWL Segments')
    plt.savefig(os.path.join(args.data_dir, 'pwl_segments.pdf'))
    plt.clf()

    # Plot number of segments for PWLs
    data_width_per_pulse = np.array([filter_pwl_table.offset_fmt.n+filter_pwl_table.slope_fmt.n for filter_pwl_table in emu.filter_pwl_tables])
    plt.plot(data_width_per_pulse)
    plt.xlabel('Step Response #')
    plt.ylabel('Data Width')
    plt.savefig(os.path.join(args.data_dir, 'pwl_data_width.pdf'))
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
        plt.savefig(os.path.join(args.data_dir, 'step_resp_{}.pdf'.format(k)))
        plt.clf()

if __name__=='__main__':
    main()
