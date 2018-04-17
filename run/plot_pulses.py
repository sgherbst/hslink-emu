import numpy as np
import logging, sys
from math import ceil, floor, log2
from scipy.interpolate import interp1d
import cvxpy

from scipy.signal import fftconvolve
from msemu.fixed import Fixed, WidthFormat
from msemu.cmd import get_parser
from msemu.pwl import Waveform

import matplotlib.pyplot as plt
import os.path


def main(tau=1, fmts=['png', 'eps', 'pdf']):

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    def save(name):
        plot_name = os.path.join(args.fig_dir, name)
        for fmt in fmts:
            plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')
            print('saving')

    t = [0, 1, 4, 6, 7, 10]
    x = [0, 1, 2, 3, 0, 0]

    num = 1000
    t_vec = np.linspace(t[0], t[-1], num)
    in_vec = interp1d(t, x, kind='zero')(t_vec)

    f, axarr = plt.subplots(2, sharex=True)
    plt.subplots_adjust(hspace=0.45)

    axarr[0].step(t_vec, in_vec, '-k')
    axarr[0].set_xticks([])
    axarr[0].set_yticks([])
    axarr[0].set_ylim([-1, 4])

    imp_vec = np.where(t_vec<=1, np.zeros(t_vec.shape), np.exp(-t_vec))
    axarr[1].plot(t_vec, imp_vec, '-k')
    axarr[1].set_xticks([])
    axarr[1].set_yticks([])

    save('pulse_in_and_imp')
    plt.show()
    plt.clf()

    n_pulses = len(t)-3
    in_pulses = []
    out_pulses = []
    sum_of_pulses = np.zeros(t_vec.shape)
    f, axarr = plt.subplots(n_pulses, sharex=True)
    plt.subplots_adjust(hspace=0.3)

    for k in range(1, n_pulses+1):
        in_pulse = interp1d([t[0], t[k], t[k+1], t[-1]], [0, x[k], 0, 0], kind='zero')(t_vec)
        out_pulse = fftconvolve(in_pulse, imp_vec)[:num]*(t_vec[1]-t_vec[0])
        axarr[k-1].plot(t_vec, out_pulse, '-k')
        axarr[k-1].set_ylim([-.1, max(x)/9+0.4])
        axarr[k-1].set_xticks([])
        axarr[k-1].set_yticks([])
        in_pulses.append(in_pulse)
        out_pulses.append(out_pulse)
        sum_of_pulses += out_pulse

    save('pulse_indiv_pulses')
    plt.show()
    plt.clf()

    plt.plot(t_vec, sum_of_pulses, '-k')
    plt.xticks([])
    plt.yticks([])
    save('pulse_sum_of_pulses')
    plt.show()
    plt.clf()

if __name__=='__main__':
    main()
