import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import fftconvolve
from math import ceil, floor, log2
import logging, sys
import os.path
import pathlib
import collections
import json

from msemu.fixed import Fixed, PointFormat, WidthFormat
from msemu.pwl import Waveform, PwlTable

class JitterFormat(Fixed):
    def __init__(self, jitter_pkpk_max, time_fmt):
        # compute jitter format
        # it is set up so that the min and max values are the absolute min and max possible in the representation,
        # since a PRBS will be used to generate them
        jitter_min_int = time_fmt.point_fmt.intval(-jitter_pkpk_max/2, floor)
        jitter_max_int = time_fmt.point_fmt.intval(+jitter_pkpk_max/2, ceil)
        jitter_width = max(WidthFormat.width([jitter_min_int, jitter_max_int], signed=True))

        super().__init__(point_fmt=time_fmt.point_fmt,
                         width_fmt=WidthFormat(jitter_width, signed=True))

class Clock:
    def __init__(self, period_fmt, jitter_fmt):
        # save period and jitter formats
        self.period_fmt = period_fmt
        self.jitter_fmt = jitter_fmt

        # compute output format
        self.update_fmt = (self.period_fmt.to_signed() + self.jitter_fmt).to_unsigned()

        # make sure that period is always positive
        assert self.update_fmt.min_int > 0

class TxClock(Clock):
    def __init__(self, freq, jitter_pkpk_max, time_fmt):
        # determine jitter format
        jitter_fmt = JitterFormat(jitter_pkpk_max=jitter_pkpk_max, time_fmt=time_fmt)

        # compute period format
        self.T_nom_int = time_fmt.intval(1/freq) 
        period_fmt = Fixed(point_fmt=time_fmt.point_fmt,
                           width_fmt=WidthFormat.make(self.T_nom_int, signed=False))

        super().__init__(period_fmt=period_fmt, jitter_fmt=jitter_fmt)

class RxClock(Clock):
    def __init__(self, fmin, fmax, bits, jitter_pkpk_max, time_fmt, phases=2):
        # store settings
        self.fmin = fmin
        self.fmax = fmax
        self.phases = phases

        # determine jitter format
        jitter_fmt = JitterFormat(jitter_pkpk_max=jitter_pkpk_max/self.phases, time_fmt=time_fmt)

        # determine DCO code format
        self.code_fmt = Fixed(point_fmt=PointFormat(0),
                              width_fmt=WidthFormat(n=bits, signed=False))

        # create DCO transfer function
        self.create_dco_tf()

        # create PWL table to represent transfer function
        self.pwl_table = self.get_pwl_table(time_point_fmt = time_fmt.point_fmt)

        # determine the period format
        period_fmt = self.pwl_table.out_fmt.to_unsigned()
        
        super().__init__(period_fmt=period_fmt,
                         jitter_fmt=jitter_fmt)

    def create_dco_tf(self):
        # generate the DCO transfer function
        codes = np.arange(self.code_fmt.max_int+2) # one extra code is included for purposes of generating the PWL table
        freqs = self.fmin + (self.fmax-self.fmin)*codes/(self.code_fmt.max_int)
        periods = 1/(self.phases*freqs)

        # check period validity
        assert np.all(periods > 0)

        # generate "waveform" representing DCO transfer function
        self.dco_tf = Waveform(t=codes, v=periods)

    def get_pwl_table(self, time_point_fmt, addr_bits_max=18, scale_factor=1e-12):
        # set tolerance for approximation by pwl segments
        min_step = np.min(np.abs(np.diff(self.dco_tf.v)))
        pwl_tol = 0.5*time_point_fmt.res

        # iterate over the number of ROM address bits
        rom_addr_bits = 1
        while (rom_addr_bits <= addr_bits_max) and (rom_addr_bits < self.code_fmt.n):
            # compute the pwl addr format
            high_bits_fmt = Fixed(width_fmt=WidthFormat(rom_addr_bits, signed=False),
                                  point_fmt=PointFormat(self.code_fmt.point - (self.code_fmt.n - rom_addr_bits)))
            low_bits_fmt = Fixed(width_fmt=WidthFormat(self.code_fmt.n - rom_addr_bits, signed=False),
                                 point_fmt=self.code_fmt.point_fmt)

            # calculate a list of times for the segment start times
            codes =  np.arange(high_bits_fmt.width_fmt.max + 1) * high_bits_fmt.res

            # build pwl table
            pwl = self.dco_tf.make_pwl(times=codes, v_scale_factor=scale_factor)

            assert pwl.error > 0
            if pwl.error <= pwl_tol:
                return PwlTable(pwls=[pwl],
                                high_bits_fmt=high_bits_fmt,
                                low_bits_fmt=low_bits_fmt,
                                addr_offset_int=0,
                                offset_point_fmt=time_point_fmt,
                                slope_point_fmt=PointFormat.make(pwl_tol / low_bits_fmt.max_float))

            rom_addr_bits += 1
        else:
            raise Exception('Failed to find a suitable PWL representation.')

def main():
    time_fmt = Fixed.make([0, 10e-6], res=1e-14, signed=False)
    
    tx_clk = TxClock(freq=8e9, jitter_pkpk_max=10e-12, time_fmt=time_fmt)
    print('tx jitter:', str(tx_clk.jitter_fmt))
    print('tx period:', str(tx_clk.period_fmt))
    print()

    rx_clk = RxClock(fmin=7.5e9, fmax=8.5e9, bits=14, jitter_pkpk_max=10e-12, time_fmt=time_fmt)
    print('rx jitter:', str(rx_clk.jitter_fmt))
    print('rx period:', str(rx_clk.period_fmt))
    print('rx code:', str(rx_clk.code_fmt))
    print()

    dco_pwl_table = rx_clk.pwl_table
    print('RX_DCO_BIAS_VAL: {}'.format(dco_pwl_table.bias_ints[0]))
    print('RX_DCO_ADDR_WIDTH: {}'.format(dco_pwl_table.high_bits_fmt.n))
    print('RX_DCO_SEGMENT_WIDTH: {}'.format(dco_pwl_table.low_bits_fmt.n))
    print('RX_DCO_OFFSET_WIDTH: {}'.format(dco_pwl_table.offset_fmt.n))
    print('RX_DCO_BIAS_WIDTH: {}'.format(dco_pwl_table.bias_fmt.n))
    print('RX_DCO_SLOPE_WIDTH: {}'.format(dco_pwl_table.slope_fmt.n))
    print('RX_DCO_SLOPE_POINT: {}'.format(dco_pwl_table.slope_fmt.point))

    import matplotlib.pyplot as plt
    pwl = dco_pwl_table.pwls[0]
    t_eval = pwl.domain(1)
    plt.plot(rx_clk.dco_tf.t, rx_clk.dco_tf.v, t_eval, pwl.eval(t_eval))
    plt.show()

if __name__=='__main__':
    main()
