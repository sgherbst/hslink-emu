import matplotlib.pyplot as plt
import os.path
import sys
import logging

from msemu.cmd import get_parser
from msemu.ila import IlaData

def main(fmts=['png', 'pdf', 'eps']):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    parser.add_argument('--trim', type=float, default=1e-6, help='Amount of time to trim from beginning of waveforms.')
    args = parser.parse_args()

    fmt_dict_file = os.path.join(args.build_dir, 'fmt_dict.json')
    ila_dir_name = os.path.join(args.data_dir, 'ila', 'steady_state')
    ila_data = IlaData(ila_dir_name=ila_dir_name, fmt_dict_file=fmt_dict_file)

    filter_out = ila_data.rxp.filter_out.start_after(args.trim)
    comp_in = ila_data.rxp.comp_in.start_after(args.trim)

    plt.hist(comp_in.v, 100, normed=1, facecolor='blue', alpha=1, label='DFE Output')
    plt.hist(filter_out.v, 100, normed=1, facecolor='green', alpha=0.5, label='CTLE Output')
    plt.legend(loc='upper center')

    plt.xlabel('Voltage')
    plt.ylabel('Probability Density')
    plt.title('RX Signal Histograms')

    plot_name = os.path.join(args.fig_dir, 'rx_histograms')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')

    plt.show()
    
if __name__=='__main__':
    main()
