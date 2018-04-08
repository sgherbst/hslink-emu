from numpy import convolve
import numpy as np
from math import pi
from msemu.tf import my_abcd
from scipy.signal import impulse
from scipy.signal import fftconvolve

from msemu.rf import get_sample_s4p, s4p_to_impulse, imp2step
from msemu.pwl import Waveform

class RxCTLE:
    def __init__(self, fp1=2e9, fp2=8e9, db_vals=None):
        # save properties
        self.fp1 = fp1
        self.fp2 = fp2

        # determine settings list
        if db_vals is None:
            db_vals = [-4, -8, -12, -16]
        self.db_vals = db_vals

    @property
    def n_settings(self):
        return len(self.db_vals)

    def get_imp(self, setting, dt, T):
        # angular frequency conversion
        wp1 = 2*pi*self.fp1
        wp2 = 2*pi*self.fp2
    
        # numerator and denominator of transfer function
        gdc = RxCTLE.db2mag(self.db_vals[setting])
        num = gdc*np.array([1/(gdc*wp1), 1])
        den = convolve(np.array([1/wp1, 1]), np.array([1/wp2, 1]))
        
        # compute impulse response of CTLE
        # done with custom code due to issues with tf2ss and impulse
        sys = my_abcd((num, den))
        t, imp = impulse(sys, T=np.arange(0, T, dt))
    
        return Waveform(t=t, v=imp)

    def get_combined_step(self, setting, dt=0.1e-12, T=20e-9):
        # get channel impulse response
        s4p = get_sample_s4p()
        t_imp_ch, v_imp_ch = s4p_to_impulse(s4p, dt, T)
    
        # get ctle impulse response for this db value
        imp_ctle = self.get_imp(setting=setting, dt=dt, T=T)
        
        # compute combined impulse response
        imp_eff = fftconvolve(v_imp_ch, imp_ctle.v)[:len(t_imp_ch)]*dt
        
        # compute resulting step response
        step = Waveform(t=t_imp_ch, v=imp2step(imp=imp_eff, dt=dt))

        return step

    @staticmethod
    def db2mag(db):
        return 10.0**(db/20.0)

def main(dt=.1e-12, T=10e-9):
    import matplotlib.pyplot as plt

    rx_ctle = RxCTLE()
    imp = rx_ctle.get_imp(setting=0, dt=dt, T=T)

    plt.plot(imp.t, imp.v)
    plt.show()

if __name__=='__main__':
    main()
