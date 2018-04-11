from numpy import convolve
import numpy as np
from math import pi
from scipy.signal import impulse
from scipy.signal import fftconvolve
import logging
import sys

from msemu.tf import my_abcd
from msemu.pwl import Waveform

class RxCTLE:
    db_vals = [-4, -8, -12, -16]

    def __init__(self,
                 dt=0.1e-12,
                 T=20e-9,
                 fp1=2e9,
                 fp2=8e9):

        # save properties
        self.dt = dt
        self.T = T
        self.fp1 = fp1
        self.fp2 = fp2

        # compute all impulse responses
        self.imps = []
        for db in self.db_vals:
            logging.debug('Computing RX impulse response @ dB={:.1f}'.format(db))
            self.imps.append(self.get_imp(db=db))

    @property
    def n_settings(self):
        return len(self.db_vals)

    def get_imp(self, db):
        # angular frequency conversion
        wp1 = 2*pi*self.fp1
        wp2 = 2*pi*self.fp2
    
        # numerator and denominator of transfer function
        gdc = RxCTLE.db2mag(db)
        num = gdc*np.array([1/(gdc*wp1), 1])
        den = convolve(np.array([1/wp1, 1]), np.array([1/wp2, 1]))
        
        # compute impulse response of CTLE
        # done with custom code due to issues with tf2ss and impulse
        sys = my_abcd((num, den))
        t, imp = impulse(sys, T=np.arange(0, self.T, self.dt))
    
        return Waveform(t=t, v=imp)

    @staticmethod
    def db2mag(db):
        return 10.0**(db/20.0)

def main(dt=.1e-12, T=10e-9):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    ctle = RxCTLE()

    import matplotlib.pyplot as plt
    plt.plot(ctle.imps[0].t, ctle.imps[0].v)
    plt.show()

if __name__=='__main__':
    main()
