import matplotlib.pyplot as plt
import os.path
import sys
import logging
from matplotlib.colors import hsv_to_rgb

from msemu.cmd import get_parser
from msemu.ila import IlaData
from msemu.ctle import RxDynamics

def main(fmts=['png', 'pdf', 'eps']):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    rx_dyn = RxDynamics(dir_name=args.channel_dir)
    gains = range(rx_dyn.rx_ctle.n)

    for k, rx_setting in enumerate(gains):
        hue = (1 - (k/(rx_dyn.rx_ctle.n-1)))/3 + 2/3
        color = hsv_to_rgb([hue, 0.9, 0.8])

        step = rx_dyn.get_step(rx_setting)
        db = rx_dyn.rx_ctle.db_vals[rx_setting]
        plt.plot(step.t*1e9, step.v, label='{} dB'.format(db), color=color)

    plt.xlabel('Time (ns)')
    plt.xlim([0, 10])
    plt.ylabel('Value')
    plt.title('Combined Channel and CTLE Step Responses')

    plot_name = os.path.join(args.fig_dir, 'rx_steps')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')

    plt.show()
    
if __name__=='__main__':
    main()
