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

class JitterFormat(Fixed):
    def __init__(self, jitter_pkpk, time_fmt):
        # compute jitter format
        # it is set up so that the min and max values are the absolute min and max possible in the representation,
        # since a PRBS will be used to generate them
        jitter_min_int = time_fmt.point_fmt.intval(0, floor)
        jitter_max_int = time_fmt.point_fmt.intval(jitter_pkpk, ceil)
        jitter_width = max(WidthFormat.width([jitter_min_int, jitter_max_int], signed=False))
        super().__init__(point_fmt=time_fmt.point_fmt,
                         width_fmt=WidthFormat(jitter_width, signed=False))

    @property
    def mid_int(self):
        return (self.min_int+self.max_int)//2

    @property
    def mid_float(self):
        return self.mid_int * self.res

class Clock:
    def __init__(self, period_fmt, jitter_fmt):
        # save period and jitter formats
        self.period_fmt = period_fmt
        self.jitter_fmt = jitter_fmt

        # compute output format
        self.out_fmt = self.period_fmt + self.jitter_fmt

        # make sure that period is always positive
        assert self.out_fmt.min_int > 0

class TxClock(Clock):
    def __init__(self, freq, jitter_pkpk, time_fmt):
        # determine jitter format
        jitter_fmt = JitterFormat(jitter_pkpk=jitter_pkpk, time_fmt=time_fmt)

        # compute period format
        self.T_nom_int = time_fmt.intval(1/freq) - jitter_fmt.mid_int
        period_fmt = Fixed(point_fmt=time_fmt.point_fmt,
                           width_fmt=WidthFormat.make(self.T_nom_int, signed=False))

        super().__init__(period_fmt=period_fmt, jitter_fmt=jitter_fmt)

class RxClock(Clock):
    def __init__(self, fmin, fmax, bits, jitter_pkpk, time_fmt, phases=2):
        # determine jitter format
        jitter_fmt = JitterFormat(jitter_pkpk=jitter_pkpk/phases, time_fmt=time_fmt)

        # determine DCO code format
        self.code_fmt = Fixed(point_fmt=PointFormat(0),
                              width_fmt=WidthFormat(n=bits, signed=False))

        # determine the slope
        t_min_no_jitter = 1/(phases*fmax)
        t_max_no_jitter = 1/(phases*fmin)
        slope = (t_max_no_jitter - t_min_no_jitter)/self.code_fmt.max_float
        assert slope > 0

        # determine slope representation
        slope_res = 0.5*slope/self.code_fmt.max_float
        self.slope_fmt = Fixed.make(slope, res=slope_res, signed=False) 

        # determine offset representation
        offset = t_max_no_jitter - jitter_fmt.mid_float
        self.offset_fmt = time_fmt.point_fmt.to_fixed(offset, signed=False)
        
        # determine period format
        period_fmt = self.offset_fmt - (self.code_fmt * self.slope_fmt).align_to(self.offset_fmt.point)

        super().__init__(period_fmt=period_fmt, jitter_fmt=jitter_fmt)

def main():
    time_fmt = Fixed.make([0, 10e-6], res=1e-14, signed=False)
    
    tx_clk = TxClock(freq=8e9, jitter_pkpk=10e-12, time_fmt=time_fmt)
    print('tx jitter:', str(tx_clk.jitter_fmt))
    print('tx period:', str(tx_clk.period_fmt))
    print()

    rx_clk = RxClock(fmin=7.5e9, fmax=8.5e9, bits=14, jitter_pkpk=10e-12, time_fmt=time_fmt)
    print('rx jitter:', str(rx_clk.jitter_fmt))
    print('rx period:', str(rx_clk.period_fmt))
    print('rx code:', str(rx_clk.code_fmt))
    print('rx slope:', str(rx_clk.slope_fmt))
    print('rx offset:', str(rx_clk.offset_fmt))

if __name__=='__main__':
    main()
