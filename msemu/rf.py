import numpy as np
from scipy.interpolate import interp1d
from scipy.fftpack import ifft
import logging, sys
from math import log2, ceil
import os.path
import wget
from scipy.integrate import cumtrapz

from skrf import Network

def s2sdd(s):
    """ Converts a 4-port single-ended S-parameter matrix
    to a 2-port differential mode representation.
    Reference: https://www.aesa-cortaillod.com/fileadmin/documents/knowledge/AN_150421_E_Single_ended_S_Parameters.pdf
    """

    sdd = np.zeros((2, 2), dtype=np.complex128)
    sdd[0, 0] = 0.5*(s[0, 0] - s[0, 2] - s[2, 0] + s[2, 2])
    sdd[0, 1] = 0.5*(s[0, 1] - s[0, 3] - s[2, 1] + s[2, 3])
    sdd[1, 0] = 0.5*(s[1, 0] - s[1, 2] - s[3, 0] + s[3, 2])
    sdd[1, 1] = 0.5*(s[1, 1] - s[1, 3] - s[3, 1] + s[3, 3])

    return sdd


def s2tf(s, zo, zs, zl):
    """ Converts a two-port S-parameter matrix to a transfer function,
    given characteristic impedance, input impedance, and output
    impedance.
    Reference: https://www.mathworks.com/help/rf/ug/s2tf.html
    """

    gamma_l = (zl-zo)/(zl+zo)
    gamma_s = (zs-zo)/(zs+zo)
    gamma_in = s[0,0]+(s[0,1]*s[1,0]*gamma_l/(1-s[1,1]*gamma_l))

    tf = ((zs + np.conj(zs))/np.conj(zs))*(s[1,0]*(1+gamma_l)*(1-gamma_s))/(2*(1-s[1,1]*gamma_l)*(1-gamma_in*gamma_s))

    return tf

def is_mostly_real(v, ratio=1e-6):
    return np.all(np.abs(np.imag(v)/np.real(v)) < ratio)

def get_impulse(f, tf, dt, T):
    """ Calculates the impulse response, given a single-sided transfer function.
    f should be non-negative and increasing.  See https://www.overleaf.com/read/mxxtgdvkmkvt
    """

    # calculate number of points
    n = int(round(2 ** (ceil(log2(T / dt)))))
    logging.debug('Number of IFFT points: {}'.format(n))

    # calculate frequency spacing
    df = 1/(n*dt)

    # copy f and tf vectors so they can be modified
    f = f.copy()
    tf = tf.copy()

    # make sure that the DC component is real if present
    if f[0] == 0:
        logging.debug('Removing imaginary part of tf[0]')

        assert is_mostly_real(tf[0])
        tf[0] = tf[0].real

    # calculate magnitude and phase
    ma = np.abs(tf)
    ph = np.unwrap(np.angle(tf))

    # add DC component if necessary
    if f[0] != 0:
        logging.debug('Adding point f[0]=0, tf[0]=abs(tf[1])')

        f = np.concatenate(([0], f))
        ma = np.concatenate(([ma[0]], ma))
        ph = np.concatenate(([0], ph))

    # interpolate magnitude and phase
    logging.debug('Interpolating magnitude and phase.')
    f_interp = np.arange(n/2)*df
    ma_interp = interp1d(f, ma, bounds_error=False, fill_value=(ma[0], 0))(f_interp)
    ph_interp = interp1d(f, ph, bounds_error=False, fill_value=(0, 0))(f_interp)

    # create frequency response vector needed for IFFT
    logging.debug('Creating the frequency response vector.')
    Gtilde = np.zeros(n, dtype=np.complex128)
    Gtilde[:(n//2)] = ma_interp * np.exp(1j*ph_interp)
    Gtilde[((n//2)+1):] = np.conjugate(Gtilde[((n//2)-1):0:-1])

    # compute impulse response
    y_imp = n*df*ifft(Gtilde)

    # check that the impulse response is real to within numerical precision
    if not is_mostly_real(y_imp):
       raise Exception('IFFT contains unacceptable imaginary component.')
    y_imp = np.real(y_imp)

    return y_imp

def imp2step(imp, dt):
    step = cumtrapz(imp, initial=0)*dt

    return step

def s4p_to_impulse(s4p, dt, T, zs=50, zl=50):
    # read S-parameter file
    ntwk = Network(s4p)

    # extract characteristic impedance
    # assumed to be the same for all 16 measurements
    z0 = ntwk.z0[0, 0]

    # extract frequency list
    freq = ntwk.frequency.f

    # extract transfer function
    tf = np.array([s2tf(s2sdd(s), 2 * z0, 2 * zs, 2 * zl) for s in ntwk.s])

    # get impulse response
    y_imp = get_impulse(freq, tf, dt, T)

    return y_imp

def get_sample_s4p():
    website = 'http://www.ece.tamu.edu/~spalermo/ecen689/'
    data_file_name = 'peters_01_0605_B12_thru.s4p'

    this_path = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(os.path.join(this_path, os.pardir, 'data'))
    data_file_path = os.path.abspath(os.path.join(data_dir, data_file_name))

    logging.debug('Checking if sample data is available.')
    if not os.path.isfile(data_file_path):
        logging.debug('Downloading sample data.')
        url = website+data_file_name
        wget.download(url, data_dir)

    return data_file_path

def main(dt=.1e-12, T=20e-9):
    import matplotlib.pyplot as plt

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    s4p = get_sample_s4p()

    y_imp = s4p_to_impulse(s4p, dt, T)
    y_step = imp2step(y_imp, dt)

    plt.plot(dt*np.arange(len(y_step)), y_step)
    plt.show()

if __name__ == '__main__':
    main()