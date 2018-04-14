import matplotlib.pyplot as plt
import os.path
import sys
import logging

from msemu.cmd import get_parser
from msemu.ila import IlaData

def main(fmts=['png', 'pdf', 'eps']):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    fmt_dict_file = os.path.join(args.build_dir, 'fmt_dict.json')
    ila_dir_name = os.path.join(args.data_dir, 'ila', 'small_step')
    ila_data = IlaData(ila_dir_name=ila_dir_name, fmt_dict_file=fmt_dict_file)

    dco_code = ila_data.rxp.dco_code

    plt.plot(dco_code.t[1:]*1e9, dco_code.v[1:])

    plt.xlabel('Time (ns)')
    plt.ylabel('DCO Code')
    plt.title('RX Startup Transient')

    plot_name = os.path.join(args.fig_dir, 'rx_startup_transient')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt)

    plt.show()
    
if __name__=='__main__':
    main()
