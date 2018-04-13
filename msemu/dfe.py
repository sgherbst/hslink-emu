import numpy as np
from math import floor
import logging, sys
from scipy.interpolate import interp1d
from scipy.signal import fftconvolve

from msemu.fixed import Fixed, PointFormat, WidthFormat
from msemu.pwl import Waveform

class PulseResp(Waveform):
    def __init__(self, t, v, ui):
        super().__init__(t=t, v=v)

        # save additional settings
        self.ui = ui

        # placeholder for memoization
        self._samp_point = None

    @property
    def samp_point(self):
        if self._samp_point is None:
            idx = np.argmax(self.v)
            self._samp_point = self.t[idx], self.v[idx]

        return self._samp_point

    @property
    def t_samp(self):
        return self.samp_point[0]

    @property
    def v_samp(self):
        return self.samp_point[1]

    def get_isi(self, n=None):
        # calculate number of UI on both sides of the sampling point
        n_post = int(floor((self.t[-1]-self.t_samp)/self.ui))

        # if desired, only calculate the first n points...
        if n is not None:
            n_post = min(n, n_post)

        # determine the times at which the pulse response is sampled
        t_isi = self.t_samp + self.ui*np.arange(1, n_post+1)

        # interpolate the waveform at those times
        v_isi = interp1d(self.t, self.v)(t_isi)

        return v_isi

class TxPulseGen:
    def __init__(
        self,
        tx_ffe,
        ui=125e-12,
        dt=0.1e-12,
        T=20e-9
    ):
        # save settings
        self.tx_ffe = tx_ffe
        self.dt = dt
        self.T = T
        self.ui = ui

        # interpolation time vector
        self.interp_t = np.arange(0, self.T, self.dt)

        # zero-order hold time points
        self.zoh_t = np.arange(self.tx_ffe.n_taps+1)*self.ui
        self.zoh_t = np.concatenate((self.zoh_t, [self.interp_t[-1]]))

        # placeholder for memoized pulses
        self._pulses = {}

    def get_pulse(self, setting):
        if setting in self._pulses:
            return self._pulses[setting]

        logging.debug('Computing TX FFE pulse @ setting {}'.format(setting))

        # define values of zero-order hold
        zoh_v = np.array(self.tx_ffe.tap_table[setting])
        zoh_v = np.concatenate((zoh_v, [0, 0]))

        # calculate pulse
        pulse_v = interp1d(self.zoh_t, zoh_v, kind='zero')(self.interp_t)

        return Waveform(t=self.interp_t, v=pulse_v)

class DfeDesigner:
    def __init__(self, tx_ffe, rx_dyn, ui=125e-12):
        # save settings
        self.rx_dyn = rx_dyn
        self.tx_ffe = tx_ffe
        self.ui = ui

        # create pulse generator
        self.tx_pulse_gen = TxPulseGen(self.tx_ffe, ui=ui, dt=self.rx_dyn.dt, T=self.rx_dyn.T)

        # placeholder for memoization
        self._resp = {}

    def get_resp(self, tx_setting, rx_setting):
        if tx_setting in self._resp:
            if rx_setting in self._resp[tx_setting]:
                return self._resp[tx_setting][rx_setting]
            else:
                pass
        else:
            self._resp[tx_setting] = {}

        logging.debug('Computing system pulse response @ tx={}, rx={}'.format(tx_setting, rx_setting))

        # get pulse and impulse response
        pulse = self.tx_pulse_gen.get_pulse(tx_setting)
        imp = self.rx_dyn.get_imp(rx_setting)

        # make sure that dt values match
        dt = pulse.dt
        assert np.isclose(dt, imp.dt)

        # compute response
        resp_v = (fftconvolve(pulse.v, imp.v)[:len(pulse.t)]) * dt
        resp = PulseResp(t=pulse.t, v=resp_v, ui=self.ui)

        self._resp[tx_setting][rx_setting] = resp

        return resp

class DFE:
    def __init__(self, tx_ffe, rx_dyn, ui, n_taps=2):
        # save settings
        self.tx_ffe = tx_ffe
        self.rx_dyn = rx_dyn
        self.ui = ui
        self.n_taps = n_taps

        # create DFE designer object to help calculate the tap values
        self.dfe_des = DfeDesigner(tx_ffe=tx_ffe, rx_dyn=rx_dyn, ui=ui)

        # create array of all DFE taps
        self._settings = None

    @property
    def tx_setting_width(self):
        return self.tx_ffe.setting_width

    @property
    def rx_setting_width(self):
        return self.rx_dyn.setting_width

    @property
    def tx_setting_padding(self):
        return self.tx_ffe.setting_padding

    @property
    def rx_setting_padding(self):
        return self.rx_dyn.setting_padding

    @property
    def settings(self):
        if self._settings is None:
            self._settings = self._create_settings()

        return self._settings

    # expensive function... computes all of the entries in the DFE table
    def _create_settings(self):
        settings = []

        # iterate over TX settings
        for tx_setting in range(1 << self.tx_setting_width):
            settings.append([])

            # iterate over RX settings
            for rx_setting in range(1 << self.rx_setting_width):

                # if this entry isn't real, just fill this part of the table with zeros
                if (tx_setting >= self.tx_ffe.n_settings) or (rx_setting >= self.rx_dyn.n):
                    settings[-1].append([0]*(1<<self.n_taps))
                    continue

                # otherwise calculate the appropriate taps
                settings[-1].append([])

                # compute pulse response with this TX/RX setting
                resp = self.dfe_des.get_resp(tx_setting=tx_setting, rx_setting=rx_setting)

                # compute ISI for this pulse response
                isi = resp.get_isi(self.n_taps)

                # iterate over all input histories
                for hist in range(1<<self.n_taps):
                    settings[-1][-1].append(0)

                    # iterate over each bit in the input history
                    for k in range(self.n_taps):
                        if ((hist >> k) & 1) == 1:
                            # if input was high, *subtract* the isi
                            settings[-1][-1][-1] -= isi[k]
                        else:
                            # if input was low, *add* the isi
                            settings[-1][-1][-1] += isi[k]

        return settings

    def write_table(self, file_name, fixed_format):
        with open(file_name, 'w') as f:
            # write the bias values into a table
            for tx_setting in range(1 << self.tx_setting_width):
                for rx_setting in range(1 << self.rx_setting_width):
                    for setting in self.settings[tx_setting][rx_setting]:
                        setting_str = fixed_format.bin_str(setting)
                        f.write(setting_str + '\n')

def main(ui=125e-12, n=10):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    # get a sample impulse response
    from msemu.ctle import RxDynamics
    from msemu.tx_ffe import TxFFE

    rx_dyn = RxDynamics(dir_name='../channel/')
    tx_ffe = TxFFE()
    dfe = DFE(rx_dyn=rx_dyn, tx_ffe=tx_ffe, ui=ui)

    # create ROM
    point_fmt = PointFormat.make(1e-3)

    # compute tap representations
    coeff_fmts = []
    for tx_setting in range(tx_ffe.n_settings):
        for rx_setting in range(rx_dyn.n):
            setting = dfe.settings[tx_setting][rx_setting]
            coeff_fmts.append(Fixed(point_fmt=point_fmt,
                                    width_fmt=WidthFormat.make(point_fmt.intval(setting), signed=True)))

    # define the input format
    coeff_fmt = Fixed.cover(coeff_fmts)
    print('coeff_fmt:', str(coeff_fmt))

    # write ROM
    dfe.write_table(file_name='../build/roms/dfe_rom.mem', fixed_format=coeff_fmt)

    # get the sampling point
    resp = dfe.dfe_des.get_resp(7, 0)
    v_isi = resp.get_isi(n=n)

    # plot results
    import matplotlib.pyplot as plt

    plt.plot(resp.t, resp.v)
    plt.plot(resp.t_samp, resp.v_samp, 'o')
    plt.plot(resp.t_samp + np.arange(1, n+1)*ui, v_isi, '*')
    plt.show()

if __name__=='__main__':
    main()
