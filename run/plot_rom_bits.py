import matplotlib.pyplot as plt
import os.path
import sys
import logging
import numpy as np
from matplotlib.colors import hsv_to_rgb
from math import ceil

from msemu.cmd import get_parser
from msemu.ila import IlaData
from msemu.verilog import VerilogPackage
from msemu.resources import ResourceCSV, ResourceAllocation, Utilization

def main(fmts=['png', 'pdf', 'eps']):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    r = ResourceCSV(os.path.join(args.data_dir, 'resource_utilization_short.csv'))
    segment_roms = [Utilization(match[1]) for match in r.get_matches(r'segment_rom_i')]
    bram_dict = {}
    for rom in segment_roms:
        if rom.bram not in bram_dict:
            bram_dict[rom.bram] = 0
        bram_dict[rom.bram] += 1
    print('BRAM Dict:', bram_dict)

    pack = VerilogPackage.from_file(os.path.join(args.build_dir, 'filter_package.sv'))

    n_ui = pack.get('NUM_UI').value

    rx_setting_width = pack.get('RX_SETTING_WIDTH').value

    filter_addr_widths = pack.get('FILTER_ADDR_WIDTHS')
    filter_offset_widths = pack.get('FILTER_OFFSET_WIDTHS')
    filter_slope_widths = pack.get('FILTER_SLOPE_WIDTHS')

    half_bram_kb = (1 << 10) * 18 / 1e3

    bits_kb = np.zeros(n_ui)
    half_bram_util = {}

    for k in range(n_ui):
        n_cols = filter_offset_widths.value[k] + filter_slope_widths.value[k]
        n_rows = 1 << (rx_setting_width + filter_addr_widths.value[k])
        bits_kb[k] = n_rows * n_cols / 1.0e3

        n_half_bram = int(ceil(bits_kb[k]/half_bram_kb))
        if n_half_bram not in half_bram_util:
            half_bram_util[n_half_bram] = 0
        half_bram_util[n_half_bram] += 1

    print(half_bram_util)

    max_half_brams = max(half_bram_util.keys())

    plt.plot(bits_kb)
    for k in range(1,max_half_brams+1):
        hue = (1 - (k-1)/(max_half_brams-1))/3
        color = hsv_to_rgb([hue, 0.9, 0.8])
        plt.plot([0, n_ui-1], [k*half_bram_kb, k*half_bram_kb], '--', color=color)
        plt.text(0, (k+0.1)*half_bram_kb, '{:0.1f} BRAM'.format(k/2))

    plt.xlabel('Tap #')
    plt.ylabel('Required ROM Size (kb)')
    plt.ylim([-half_bram_kb*0.2, (max_half_brams+0.3)*half_bram_kb])
    plt.title('Bits Requirement for Step Response Storage')

    plot_name = os.path.join(args.fig_dir, 'rom_bits_postprocess')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')

    plt.show()
    
if __name__=='__main__':
    main()
