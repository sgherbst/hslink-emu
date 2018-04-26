import matplotlib.pyplot as plt
import os.path
import sys
import logging
import numpy as np

from msemu.cmd import get_parser
from msemu.ila import IlaData

def find_settling(t, v, vss, frac):
    error = np.abs((v-vss)/vss)
    idx_rev = np.argmax(error[::-1] > frac)
    idx = len(v) - idx_rev # one index ahead of idx_rev
    assert error[idx] <= frac
    assert error[idx-1] > frac
    return t[idx]

def main(fmts=['png', 'pdf', 'eps']):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    f, (ax1, ax2) = plt.subplots(1, 2, sharey=True)

    # read from FPGA
    fmt_dict_file = os.path.join(args.build_dir, 'fmt_dict.json')
    ila_dir_name = os.path.join(args.data_dir, 'ila', 'large_step')
    ila_data = IlaData(ila_dir_name=ila_dir_name, fmt_dict_file=fmt_dict_file)
    dco_code = ila_data.rxp.dco_code

    ax1.plot(dco_code.t[1:]*1e9, dco_code.v[1:], color='slateblue')
    ax1.set_xlabel('Time (ns)')
    ax1.set_xlim([0, 1000])
    ax1.set_ylabel('DCO Code')
    ax1.set_title('FPGA Emulation')

    print('FPGA Settling Time: {:0.3f} us'.format(1e6*find_settling(dco_code.t[1:], dco_code.v[1:], 8192, 0.1)))

    # read from simulation
    mat = np.load(os.path.join(args.data_dir, 'LargeStepPySim.npy'))

    ax2.plot(mat[:, 0] * 1e9, mat[:, 1], color='seagreen')
    ax2.set_xlabel('Time (ns)')
    ax2.set_xlim([0, 1000])
    ax2.set_title('CPU Simulation')

    print('CPU Settling Time: {:0.3f} us'.format(1e6*find_settling(mat[:, 0], mat[:, 1], 8192, 0.1)))

    plot_name = os.path.join(args.fig_dir, 'rx_startup_transient')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')

    plt.show()
    
if __name__=='__main__':
    main()
