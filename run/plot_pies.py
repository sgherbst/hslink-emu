import matplotlib.pyplot as plt
import os.path
import sys
import logging
import re

from msemu.cmd import get_parser

from msemu.resources import ResourceCSV, ResourceAllocation

def main(fmts=['png', 'pdf', 'eps']):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    r = ResourceCSV(os.path.join(args.data_dir, 'resource_utilization_short.csv'))

    # top level resources

    alloc = ResourceAllocation(r.get_util('dut'))

    alloc.add(r.get_util('dbg_hub'), 'Debug')
    alloc.add(r.get_util('ila_0_i'), 'Debug')
    alloc.add(r.get_util('ila_1_i'), 'Debug')
    alloc.add(r.get_util('ila_2_i'), 'Debug')
    alloc.add(r.get_util('vio_0_i'), 'Debug')

    alloc.add(r.get_util('filter_i'), 'Filter')

    alloc.plot()
    plot_name = os.path.join(args.fig_dir, 'top_level_resources')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')
    plt.show()
    plt.clf()

    # filter resources

    alloc = ResourceAllocation(r.get_util('filter_i'))

    alloc.add(r.get_utils(r'gen_pwl_blocks\[\d+\]\.pwl_k'), 'PWL Blocks')
    alloc.add(r.get_utils(r'gen_pwl_blocks\[\d+\]\.prod_k'), 'Pulse Products')

    alloc.add(r.get_util('sum_i'), 'Sum')

    alloc.plot()
    plot_name = os.path.join(args.fig_dir, 'filter_resources')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')
    plt.show()

if __name__=='__main__':
    main()
