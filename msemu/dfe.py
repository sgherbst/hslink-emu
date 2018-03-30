import numpy as np
from math import floor
import logging, sys
from scipy.interpolate import interp1d

def get_samp_point(t, v):
    idx = np.argmax(v)
    return t[idx], v[idx]

def get_isi(t, v, ui, t_samp=None, where='both'):
    # find sampling point if necessary
    if t_samp is None:
        t_samp, _ = get_samp_point(t, v)

    # calculate number of UI on both sides of the sampling point
    n_pre = int(floor((t_samp-t[0])/ui))
    n_post = int(floor((t[-1]-t_samp)/ui))

    if where.lower() in ['pre']:
        t_isi = t_samp - ui*np.arange(1, n_pre+1)
    elif where.lower() in ['post']:
        t_isi = t_samp + ui*np.arange(1, n_post+1)
    elif where.lower() in ['both']:
        t_isi = t_samp + ui*np.concatenate((-np.arange(1, n_pre+1), np.arange(1, n_post+1)))
    else:
        raise ValueError('Invalid ISI mode.')

    v_isi = interp1d(t, v)(t_isi)

    return t_isi, v_isi

def main(ui=125e-12, dt=.1e-12, T=20e-9):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    # get a sample impulse response
    import msemu.rf
    s4p = msemu.rf.get_sample_s4p()
    t, y_imp = msemu.rf.s4p_to_impulse(s4p, dt, T)

    # generate the pulse
    in_ = interp1d([0, ui, t[-1]], [1, 0, 0], kind='zero')(t)

    # generate the pulse response
    from scipy.signal import fftconvolve
    pulse = (fftconvolve(y_imp, in_)[:len(t)])*dt

    # get the sampling point
    t_samp, v_samp = get_samp_point(t=t, v=pulse)
    t_isi, v_isi = get_isi(t=t, v=pulse, ui=ui, where='both')

    # plot results
    import matplotlib.pyplot as plt
    plt.plot(t, pulse)
    plt.plot(t_samp, v_samp, 'o')
    plt.plot(t_isi, v_isi, '*')
    plt.show()

if __name__=='__main__':
    main()
