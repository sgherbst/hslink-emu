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
    def __init__(self, finit, fmin, fmax, bits, jitter_pkpk, time_fmt, phases=2):
        # store settings
        self.finit = finit
        self.phases = phases

        # determine jitter format
        jitter_fmt = JitterFormat(jitter_pkpk=jitter_pkpk/self.phases, time_fmt=time_fmt)

        # determine DCO code format
        self.code_fmt = Fixed(point_fmt=PointFormat(0),
                              width_fmt=WidthFormat(n=bits, signed=False))

        # determine the slope
        t_min_no_jitter = 1/(self.phases*fmax)
        t_max_no_jitter = 1/(self.phases*fmin)
        self.slope_float = (t_max_no_jitter - t_min_no_jitter)/self.code_fmt.max_float
        assert self.slope_float > 0

        # determine slope representation
        slope_res = 0.5*self.slope_float/self.code_fmt.max_float
        self.slope_fmt = Fixed.make(self.slope_float, res=slope_res, signed=False) 

        # determine offset representation
        self.offset_float = t_max_no_jitter - jitter_fmt.mid_float
        self.offset_fmt = time_fmt.point_fmt.to_fixed(self.offset_float, signed=False)
        
        # determine period format
        self.prod_fmt = (self.code_fmt * self.slope_fmt).align_to(self.offset_fmt.point)
        period_fmt = self.offset_fmt - self.prod_fmt

        super().__init__(period_fmt=period_fmt, jitter_fmt=jitter_fmt)

    @property
    def slope_int(self):
        return self.slope_fmt.intval(self.slope_float)

    @property
    def offset_int(self):
        return self.offset_fmt.intval(self.offset_float)

    @property
    def code_init(self):
        tinit = 1/(self.phases*self.finit)
        retval = round((self.offset_float+self.jitter_fmt.mid_float-tinit)/self.slope_float)

        assert self.code_fmt.min_int <= retval <= self.code_fmt.max_int
        return retval

def main():
    time_fmt = Fixed.make([0, 10e-6], res=1e-14, signed=False)
    
    tx_clk = TxClock(freq=8e9, jitter_pkpk=10e-12, time_fmt=time_fmt)
    print('tx jitter:', str(tx_clk.jitter_fmt))
    print('tx period:', str(tx_clk.period_fmt))
    print()

    rx_clk = RxClock(finit=8e9, fmin=7.5e9, fmax=8.5e9, bits=14, jitter_pkpk=10e-12, time_fmt=time_fmt)
    print('rx jitter:', str(rx_clk.jitter_fmt))
    print('rx period:', str(rx_clk.period_fmt))
    print('rx product:', str(rx_clk.prod_fmt))
    print('rx code:', str(rx_clk.code_fmt))
    print('rx slope:', str(rx_clk.slope_fmt))
    print('rx offset:', str(rx_clk.offset_fmt))
    print('rx code init:', str(rx_clk.code_init))

if __name__=='__main__':
    main()
