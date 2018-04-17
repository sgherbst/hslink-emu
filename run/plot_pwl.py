import numpy as np
import logging, sys
from math import ceil, floor, log2
from scipy.interpolate import interp1d
import cvxpy

from msemu.fixed import Fixed, WidthFormat
from msemu.cmd import get_parser
from msemu.pwl import Waveform

def main(tau=1, fmts=['png', 'eps', 'pdf']):

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    t = np.linspace(0*tau, 3*tau, 1e3)
    v = np.exp(t/tau)

    ts = 0.5*tau
    tf = 2.5*tau

    wave = Waveform(t=t, v=v)
    times = np.linspace(t[0], t[-1], 5)[:-1]
    print(times)
    pwl = wave.make_pwl(times=times)
    print(pwl.offsets)
    print(pwl.slopes)

    import matplotlib.pyplot as plt
    from matplotlib.colors import hsv_to_rgb
    from mpltools import annotation

    t_eval = pwl.domain(0.01*tau)

    color = 'deepskyblue'
    linewidth = 4

    times = pwl.times
    offsets = pwl.offsets
    slopes = pwl.slopes
    for time, offset, slope in zip(times, offsets, slopes):
        plt.plot([time, time + pwl.dtau], [offset, offset + slope * pwl.dtau], linewidth=linewidth, color=color)
        plt.plot(time, offset, 'ko', markersize=4, color='lightcoral')

    dot = times[2]+pwl.dtau/2
    plt.plot(dot, pwl.eval(dot), 'ko', markersize=6, color='forestgreen')

    dot = times[2]
    slope_dt = pwl.dtau/5
    plt.plot([dot, dot, dot+slope_dt, dot], pwl.eval([dot, dot+slope_dt, dot+slope_dt, dot]), '-k')

    # plt.text(times[1], offsets[1]-.8, r'$\left(t_k - \Delta t, a_{k-1}\right)$')
    # plt.text(times[2]-.3, offsets[2]+.1, r'$\left(t_k, a_k\right)$')
    # plt.text(times[3], offsets[3]-.7, r'$\left(t_k + \Delta t, a_{k+1}\right)$')

    # annotation.slope_marker((1, 0.6), (-1, 2), ax=plt.axes())

    plt.plot(t, v, '-k', linewidth=1, label=r'$y\left(t\right)$')
    plt.legend(loc='upper left')
    #plt.xlabel('time')
    #plt.ylabel('value')
    plt.title('Piecewise-Linear Approximation')
    plt.xlim([0, 3*tau])
    plt.ylim([-2, 15])
    plt.xticks([])
    plt.yticks([])

    import os.path
    plot_name = os.path.join(args.fig_dir, 'pwl_sample_plot')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')
        print('saving')

    plt.show()

if __name__=='__main__':
    main()
