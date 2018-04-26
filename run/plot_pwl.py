import numpy as np
import logging, sys
from math import ceil, floor, log2, sqrt
from scipy.interpolate import interp1d
import cvxpy

from msemu.fixed import Fixed, WidthFormat
from msemu.cmd import get_parser
from msemu.pwl import Waveform

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.colors import hsv_to_rgb
from mpltools import annotation

def main(tau=1, fmts=['png', 'eps', 'pdf']):

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    t = np.linspace(0.125, 1, 1000)
    v = -(t-0.5)**2

    t_samp = np.linspace(t[0], t[-1], 5)
    int_func = interp1d(t, v)

    v_samp = int_func(t_samp)

    ax = plt.axes()
    for k in range(len(t_samp)-1):
        x = t_samp[k]
        y = v_samp[k]
        slope = (v_samp[k+1]-v_samp[k])/(t_samp[k+1]-t_samp[k])

        dx = sqrt(2*0.0002/abs(slope))
        dy = slope*dx
        if slope >= 0:
            pts = [[x,y], [x+dx,y], [x+dx,y+dy]]
        else:
            pts = [[x,y], [x,y+dy], [x+dx,y+dy]]

        ax.add_patch(Polygon(pts, closed=True, fill=True, color='black'))

    plt.plot(t_samp, v_samp, '-', label='PWL', color='deepskyblue')
    plt.plot(t, v, '--', label='Exact', color='lightcoral')

    for x, y in zip(t_samp, v_samp):
        plt.plot(x, y, 'o', color='forestgreen', markersize=5)

    plt.xticks([])
    plt.yticks([])

    yr = 1.3*(max(v)-min(v))
    y0 = 0.5*(max(v)+min(v))
    xr = 1.3*(max(t)-min(t))
    x0 = 0.5*(max(t)+min(t))
    plt.xlim([x0-xr/2, x0+xr/2])
    plt.ylim([y0-yr/2, y0+yr/2])
    plt.title('Piecewise-Linear Representation')
    plt.legend(loc='lower left')

    import os.path
    plot_name = os.path.join(args.fig_dir, 'pwl_sample_plot')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')
        print('saving')

    plt.show()

    # color = 'deepskyblue'
    # linewidth = 4
    #
    # times = pwl.times
    # offsets = pwl.offsets
    # slopes = pwl.slopes
    # for time, offset, slope in zip(times, offsets, slopes):
    #     plt.plot([time, time + pwl.dtau], [offset, offset + slope * pwl.dtau], linewidth=linewidth, color=color)
    #     plt.plot(time, offset, 'ko', markersize=4, color='lightcoral')
    #
    # dot = times[2]+pwl.dtau/2
    # plt.plot(dot, pwl.eval(dot), 'ko', markersize=6, color='forestgreen')
    #
    # dot = times[2]
    # slope_dt = pwl.dtau/5
    # plt.plot([dot, dot, dot+slope_dt, dot], pwl.eval([dot, dot+slope_dt, dot+slope_dt, dot]), '-k')
    #
    # # plt.text(times[1], offsets[1]-.8, r'$\left(t_k - \Delta t, a_{k-1}\right)$')
    # # plt.text(times[2]-.3, offsets[2]+.1, r'$\left(t_k, a_k\right)$')
    # # plt.text(times[3], offsets[3]-.7, r'$\left(t_k + \Delta t, a_{k+1}\right)$')
    #
    # # annotation.slope_marker((1, 0.6), (-1, 2), ax=plt.axes())
    #
    # plt.plot(t, v, '-k', linewidth=1, label=r'$y\left(t\right)$')
    # plt.legend(loc='upper left')
    # #plt.xlabel('time')
    # #plt.ylabel('value')
    # plt.title('Piecewise-Linear Approximation')
    # plt.xlim([0, 3*tau])
    # plt.ylim([-2, 15])
    # plt.xticks([])
    # plt.yticks([])
    #


if __name__=='__main__':
    main()
