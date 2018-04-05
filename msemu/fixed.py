import logging, sys
from math import log, ceil, floor, log2
import collections

def listify(val_or_vals):
    if not isinstance(val_or_vals, collections.Iterable):
        vals = [val_or_vals]
    else:
        vals = val_or_vals

    return vals

class Binary:
    def __init__(self, n):
        self.n = n

    def bin_str(self, val):
        if val < 0:
            conv_val = (1 << self.n) + val
        else:
            conv_val = val

        str_val = format(conv_val, '0' + str(self.n) + 'b')
        if len(str_val) != self.n:
            raise ValueError('Value to be converted cannot be represented: %d, %d' % (val, self.n))

        return str_val

class Unsigned(Binary):
    def __init__(self, n):
        super().__init__(n=n)

    @property
    def min(self):
        return 0

    @property
    def max(self):
        return (1<<self.n)-1

    @staticmethod
    def width(val_or_vals):
        vals = listify(val_or_vals)

        max_width = 0
        for val in vals:
            assert isinstance(val, int), "Values must be integers."
            assert val >= 0, "Unsigned values must be non-negative"
            width = int(ceil(log2(val+1)))
            max_width = max(width, max_width)

        return max_width

    @staticmethod
    def make(val_or_vals):
        n = Unsigned.width(val_or_vals)
        return Unsigned(n=n)

class Signed(Binary):
    def __init__(self, n):
        super().__init__(n=n)

    @property
    def min(self):
        return -(1<<(self.n-1))

    @property
    def max(self):
        return (1<<(self.n-1))-1

    @staticmethod
    def width(val_or_vals):
        vals = listify(val_or_vals)

        max_width = 0
        for val in vals:
            assert isinstance(val, int), "Values must be integers."
            if val < 0:
                width = int(ceil(1 + log2(-val)))
            else:
                width = int(ceil(1 + log2(val+1)))

            max_width = max(width, max_width)

        return max_width

    @staticmethod
    def make(val_or_vals):
        n = Signed.width(val_or_vals)
        return Signed(n=n)

class Fixed:
    def __init__(self, point):
        self.point = point

    @property
    def res(self):
        return Fixed.point2res(self.point)

    def float2fixed(self, val, func=None):
        if func is None:
            func = round
        return Fixed.intval(val=val, point=self.point, func=func)

    def define_width(self, val_or_vals, width_cls):
        vals = listify(val_or_vals)

        min_float = min(vals)
        max_float = max(vals)

        min_intval = self.float2fixed(val=min_float, func=floor)
        max_intval = self.float2fixed(val=max_float, func=ceil)

        fixed_fmt = Fixed(self.point)
        width_fmt = width_cls.make([min_intval, max_intval])
        return FixedWithWidth(fixed_fmt=fixed_fmt, width_fmt=width_fmt)

    @staticmethod
    def res2point(res):
        return int(ceil(-log2(res)))

    @staticmethod
    def point2res(point):
        return 2.0 ** (-point)

    @staticmethod
    def intval(val, point, func):
        scaled = val/Fixed.point2res(point)

        intval = func(scaled)
        assert isinstance(intval, int), "Problem generating integer representation"

        return intval

    @staticmethod
    def make(res):
        point = Fixed.res2point(res)
        return Fixed(point=point)

class FixedWithWidth:
    def __init__(self, fixed_fmt, width_fmt):
        self.fixed_fmt = fixed_fmt
        self.width_fmt = width_fmt

    def mul(self, other, width_cls):
        fixed_fmt = Fixed(self.fixed_fmt.point+other.fixed_fmt.point)

        intvals = [self.width_fmt.min * other.width_fmt.min,
                   self.width_fmt.min * other.width_fmt.max,
                   self.width_fmt.max * other.width_fmt.min,
                   self.width_fmt.max * other.width_fmt.max]
        width_fmt = width_cls.make(intvals)

        return FixedWithWidth(fixed_fmt=fixed_fmt, width_fmt=width_fmt)

    def add(self, other, width_cls):
        assert self.fixed_fmt.point == other.fixed_fmt.point, "Points must be aligned"
        fixed_fmt = Fixed(self.fixed_fmt.point)

        intvals = [self.width_fmt.min + other.width_fmt.min,
                   self.width_fmt.max + other.width_fmt.max]
        width_fmt = width_cls.make(intvals)

        return FixedWithWidth(fixed_fmt=fixed_fmt, width_fmt=width_fmt)

    def align_to(self, point, width_cls):
        fixed_fmt = Fixed(point)

        if self.fixed_fmt.point >= point:
            rshift = self.fixed_fmt.point - point
            intvals = [self.width_fmt.min >> rshift,
                       self.width_fmt.max >> rshift]
        else:
            lshift = point - self.fixed_fmt.point
            intvals = [self.width_fmt.min << lshift,
                       self.width_fmt.max << lshift]

        width_fmt = width_cls.make(intvals)

        return FixedWithWidth(fixed_fmt = fixed_fmt, width_fmt = width_fmt)

    def float2fixed(self, val, func=None):
        intval = self.fixed_fmt.float2fixed(val=val, func=func)
        assert self.min_int <= intval <= self.max_int, "Integer value out of range."

        return intval

    def bin_str(self, val, func=None):
        intval = self.float2fixed(val=val, func=func)
        return self.width_fmt.bin_str(intval)

    @property
    def n(self):
        return self.width_fmt.n

    @property
    def point(self):
        return self.fixed_fmt.point

    @property
    def res(self):
        return self.fixed_fmt.res

    @property
    def min_int(self):
        return self.width_fmt.min

    @property
    def max_int(self):
        return self.width_fmt.max

    @property
    def min_float(self):
        return self.min_int * self.res

    @property
    def max_float(self):
        return self.max_int * self.res

    @staticmethod
    def make(val_or_vals, res, width_cls):
        return Fixed.make(res).define_width(val_or_vals, width_cls)

def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    fmt1 = FixedWithWidth.make(3.23, 0.0001, Signed)
    print(fmt1.bin_str(-0.456))

    fmt2 = FixedWithWidth.make(7.89, 0.0001, Unsigned)

    fmt3 = fmt1.add(fmt2, Signed)
    print(fmt3.n, fmt3.point, fmt3.min_float, fmt3.max_float)

    fmt4 = fmt1.mul(fmt2, Signed)
    print(fmt4.n, fmt4.point, fmt4.min_float, fmt4.max_float)

    fmt5 = fmt4.align_to(Fixed.res2point(0.1), Signed)
    print(fmt5.n, fmt5.point, fmt5.min_float, fmt5.max_float)

if __name__=='__main__':
    main()
