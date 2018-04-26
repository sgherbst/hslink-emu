import matplotlib.pyplot as plt
import os.path
import sys
import logging
import numpy as np
from matplotlib.colors import hsv_to_rgb
from math import ceil, log2

from msemu.cmd import get_parser
from msemu.ila import IlaData
from msemu.verilog import VerilogPackage
from msemu.resources import ResourceCSV, ResourceAllocation, Utilization
from msemu.fixed import Fixed, WidthFormat, PointFormat
from msemu.pwl import PwlTable
from msemu.ctle import RxDynamics

# script to compare optimized PWL ROM utilization to just using the same PWL tables for all taps

def get_pwl_table(steps, time_point, offset_point, err_pwl=1e-3, addr_bits_max=16, max_time=10e-9, err_step=1e-4):
    yss = min(step.yss for step in steps)

    # set tolerance for approximation by pwl segments
    pwl_tol = err_pwl * yss

    # compute number of incoming bits
    time_point_fmt = PointFormat(time_point)
    pwl_time_bits = time_point_fmt.to_fixed([0, max_time], signed=False).n

    # iterate over the number of ROM address bits
    rom_addr_bits = 1
    while rom_addr_bits <= addr_bits_max:
        logging.debug('Number of segments: {}'.format(rom_addr_bits))

        # compute the pwl addr format
        high_bits_fmt = Fixed(width_fmt=WidthFormat(rom_addr_bits, signed=False),
                              point_fmt=PointFormat(time_point - (pwl_time_bits - rom_addr_bits)))
        low_bits_fmt = Fixed(width_fmt=WidthFormat(pwl_time_bits-rom_addr_bits, signed=False),
                             point_fmt=time_point_fmt)

        # calculate a list of times for the segment start times
        times = np.arange(high_bits_fmt.width_fmt.max+1)*high_bits_fmt.res

        # build pwl table
        n_check = max(1000, 2*len(times))

        pwls = [step.make_pwl(times=times, n_check=n_check) for step in steps]

        if all(pwl.error <= pwl_tol for pwl in pwls):
            return PwlTable(pwls=pwls,
                            high_bits_fmt = high_bits_fmt,
                            low_bits_fmt = low_bits_fmt,
                            addr_offset_int = 0,
                            offset_point_fmt = PointFormat(offset_point),
                            slope_point_fmt = PointFormat.make(err_step / low_bits_fmt.max_float))

        rom_addr_bits += 1
    else:
        raise Exception('Failed to find a suitable PWL representation.')

def main(fmts=['png', 'pdf', 'eps'], half_bram_size = (1 << 10) * 18):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    # get the RX dynamics model
    rx_dyn = RxDynamics(dir_name=args.channel_dir)

    # Get the step responses and record the minimum steady-state value,
    # which sets precision requirements throughout the design
    steps = []
    for k in range(rx_dyn.n):
        step = rx_dyn.get_step(k)
        steps.append(step)

    filter = VerilogPackage.from_file(os.path.join(args.build_dir, 'filter_package.sv'))
    time = VerilogPackage.from_file(os.path.join(args.build_dir, 'time_package.sv'))
    signal = VerilogPackage.from_file(os.path.join(args.build_dir, 'signal_package.sv'))

    offset_point = signal.get('FILTER_OUT_POINT').value
    time_point=time.get('TIME_POINT').value

    pwl_table = get_pwl_table(steps=steps, offset_point=offset_point, time_point=time_point)
    pwl = pwl_table.pwls[0]

    t=pwl.domain(1e-12)
    plt.plot(t, pwl.eval(t))
    plt.show()

    #n_ui = filter.get('NUM_UI').value

    bits_per_tap = pwl_table.table_size_bits
    bram_per_tap = 0.5*int(ceil(bits_per_tap/half_bram_size))
    print('Bits per tap, non-optimized: {:d}'.format(bits_per_tap))
    print('BRAM per tap, non-optimized: {:0.1f}'.format(bram_per_tap))

    # segment_roms = [Utilization(match[1]) for match in r.get_matches(r'segment_rom_i')]
    # bram_dict = {}
    # for rom in segment_roms:
    #     if rom.bram not in bram_dict:
    #         bram_dict[rom.bram] = 0
    #     bram_dict[rom.bram] += 1
    # print('BRAM Dict:', bram_dict)
    #
    # pack = VerilogPackage.from_file(os.path.join(args.build_dir, 'filter_package.sv'))
    #
    # n_ui = pack.get('NUM_UI').value
    #
    # rx_setting_width = pack.get('RX_SETTING_WIDTH').value
    #
    # filter_addr_widths = pack.get('FILTER_ADDR_WIDTHS')
    # filter_offset_widths = pack.get('FILTER_OFFSET_WIDTHS')
    # filter_slope_widths = pack.get('FILTER_SLOPE_WIDTHS')
    #
    # half_bram_kb = (1 << 10) * 18 / 1e3
    #
    # bits_kb = np.zeros(n_ui)
    # half_bram_util = {}
    #
    # for k in range(n_ui):
    #     n_cols = filter_offset_widths.value[k] + filter_slope_widths.value[k]
    #     n_rows = 1 << (rx_setting_width + filter_addr_widths.value[k])
    #     bits_kb[k] = n_rows * n_cols / 1.0e3
    #
    #     n_half_bram = int(ceil(bits_kb[k] / half_bram_kb))
    #     if n_half_bram not in half_bram_util:
    #         half_bram_util[n_half_bram] = 0
    #     half_bram_util[n_half_bram] += 1
    #
    # print(half_bram_util)
    #
    # max_half_brams = max(half_bram_util.keys())
    #
    # plt.plot(bits_kb)
    # for k in range(1, max_half_brams + 1):
    #     hue = (1 - (k - 1) / (max_half_brams - 1)) / 3
    #     color = hsv_to_rgb([hue, 0.9, 0.8])
    #     plt.plot([0, n_ui - 1], [k * half_bram_kb, k * half_bram_kb], '--', color=color)
    #     plt.text(0, (k + 0.1) * half_bram_kb, '{:0.1f} BRAM'.format(k / 2))
    #
    # plt.xlabel('Tap #')
    # plt.ylabel('Required ROM Size (kb)')
    # plt.ylim([-half_bram_kb * 0.2, (max_half_brams + 0.3) * half_bram_kb])
    # plt.title('Bits Requirement for Step Response Storage')
    #
    # plot_name = os.path.join(args.fig_dir, 'rom_bits_postprocess')
    # for fmt in fmts:
    #     plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')
    #
    # plt.show()

    # # find out how wide the offsets would need to be
    # max_bias_width = max(filter.get('FILTER_BIAS_WIDTHS').value)
    # max_biased_offset_width = max(filter.get('FILTER_OFFSET_WIDTHS').value)
    # max_offset_width = int(ceil(log2((1 << max_bias_width) + (1 << max_biased_offset_width) - 1)))
    #
    # # find out how wide the slopes would have to be
    # max_slope_point = max(filter.get('FILTER_SLOPE_POINTS').value)
    # max_slope_width = max(slope_width + (max_slope_point-slope_point) for slope_width, slope_point
    #                    in zip(filter.get('FILTER_SLOPE_WIDTHS').value, filter.get('FILTER_SLOPE_POINTS').value))
    #
    # # find out the required time resolution of the table
    # time_point = time.get('TIME_POINT').value
    # segment_widths = filter.get('FILTER_SEGMENT_WIDTHS').value
    # max_pwl_addr_point = max(time_point-segment_width for segment_width in segment_widths)
    # min_pwl_time_res = 2**(-max_pwl_addr_point)
    #
    # # find out the number of segments required
    # required_n_seg = int(round(Tstep/min_pwl_time_res))
    #
    # # find out the number of RX settings
    # num_rx_settings = filter.get('NUM_RX_SETTINGS').value
    #
    # # calculate BRAM requirement per tap



if __name__ == '__main__':
    main()
