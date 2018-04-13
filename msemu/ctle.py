from numpy import convolve
import numpy as np
from math import pi, ceil, log2
from scipy.signal import impulse
import logging
import sys

from msemu.tf import my_abcd
from msemu.pwl import Waveform
from msemu.rf import ChannelData, imp2step, get_combined_imp

class RxDynamics:
    def __init__(
        self,
        dir_name,
        dt=0.1e-12,
        T=20e-9
    ):
        # save settings
        self.dt = dt
        self.T = T

        # instantiate CTLE and channel
        self.rx_ctle = RxCTLE(dt=dt, T=T)
        self.channel_data = ChannelData(dir_name=dir_name, dt=dt, T=T)

        # placeholder for memoized results
        self._imps = {}
        self._steps = {}

    @property
    def n(self):
        return self.rx_ctle.n

    @property
    def setting_width(self):
        return self.rx_ctle.setting_width

    @property
    def setting_padding(self):
        return self.rx_ctle.setting_padding

    def get_imp(self, setting):
        # check if this impulse response has already been calculated
        if setting in self._imps:
            return self._imps[setting]

        # if not, calculate the impulse response
        logging.debug('Computing RX dynamics impulse response @ setting {}'.format(setting))

        # compute combined impulse response
        imp = get_combined_imp(self.channel_data.imp,
                               self.rx_ctle.get_imp(setting))

        # trim length to that of original channel impulse response
        imp = imp.trim(self.channel_data.imp.n)

        # memoize result
        self._imps[setting] = imp

        return imp

    def get_step(self, setting):
        # check if this step response has already been calculated
        if setting in self._steps:
            return self._steps[setting]

        # if not, calculate the step response
        logging.debug('Computing RX dynamics step response @ setting {}'.format(setting))

        # get impulse response
        imp = self.get_imp(setting=setting)

        # compute step response
        step = Waveform(
            t=imp.t,
            v=imp2step(imp=imp.v, dt=imp.dt))

        # memoize result
        self._steps[setting] = step

        return step

class RxCTLE:
    db_vals = [-4, -8, -12, -16]

    def __init__(
        self,
        dt=0.1e-12,
        T=20e-9,
        fp1=2e9,
        fp2=8e9
    ):

        # save properties
        self.dt = dt
        self.T = T
        self.fp1 = fp1
        self.fp2 = fp2

        # placeholder for memoized results
        self._imps = {}
        self._steps = {}

    @property
    def n(self):
        return len(self.db_vals)

    @property
    def setting_width(self):
        return int(ceil(log2(self.n)))

    @property
    def setting_padding(self):
        return ((1 << self.setting_width) - self.n)

    def get_imp(self, setting):
        # check if this impulse response has already been calculated
        if setting in self._imps:
            return self._imps[setting]

        # if not, calculate the impulse response
        logging.debug('Computing CTLE impulse response @ setting {}'.format(setting))

        # get corresponding dB value
        db = self.db_vals[setting]

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
        imp_t, imp_v = impulse(sys, T=np.arange(0, self.T, self.dt))

        # construct waveform object
        imp = Waveform(t=imp_t, v=imp_v)

        # memoize result
        self._imps[setting] = imp

        return imp

    @staticmethod
    def db2mag(db):
        return 10.0**(db/20.0)

def main(dt=.1e-12, T=10e-9):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    rx_dyn = RxDynamics(dir_name='../channel/')

    import matplotlib.pyplot as plt
    plt.plot(rx_dyn.get_step(0).t, rx_dyn.get_step(0).v)
    plt.show()

if __name__=='__main__':
    main()
