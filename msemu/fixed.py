import logging, sys
from math import log, ceil, floor, log2
import collections

def listify(val_or_vals):
    if not isinstance(val_or_vals, collections.Iterable):
        vals = [val_or_vals]
    else:
        vals = val_or_vals

    return vals

class WidthFormat:
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

class Unsigned(WidthFormat):
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

class Signed(WidthFormat):
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

class PointFormat:
    def __init__(self, point):
        self.point = point

    @property
    def res(self):
        return PointFormat.point2res(self.point)

    def intval(self, val, func=None):
        if func is None:
            func = round
        return PointFormat.float2int(val=val, point=self.point, func=func)

    def to_fixed(self, val_or_vals, width_cls):
        vals = listify(val_or_vals)

        min_float = min(vals)
        max_float = max(vals)

        min_intval = self.intval(val=min_float, func=floor)
        max_intval = self.intval(val=max_float, func=ceil)

        point_fmt = PointFormat(self.point)
        width_fmt = width_cls.make([min_intval, max_intval])
        return Fixed(point_fmt=point_fmt, width_fmt=width_fmt)

    @staticmethod
    def res2point(res):
        return int(ceil(-log2(res)))

    @staticmethod
    def point2res(point):
        return 2.0 ** (-point)

    @staticmethod
    def float2int(val, point, func):
        scaled = val/PointFormat.point2res(point)

        intval = int(func(scaled))
        assert isinstance(intval, int), "Problem generating integer representation."

        return intval

    @staticmethod
    def make(res):
        point = PointFormat.res2point(res)
        return PointFormat(point=point)

class Fixed:
    def __init__(self, point_fmt, width_fmt):
        self.point_fmt = point_fmt
        self.width_fmt = width_fmt

    def signed(self):
        point_fmt = PointFormat(self.point_fmt.point)

        intvals = [self.width_fmt.min,
                   self.width_fmt.max]
        width_fmt = Signed.make(intvals)

        return Fixed(point_fmt=point_fmt, width_fmt=width_fmt)

    def get_width_cls(self, other):
        if isinstance(self.width_fmt, Unsigned) and isinstance(other.width_fmt, Unsigned):
            return Unsigned
        elif isinstance(self.width_fmt, Signed) and isinstance(other.width_fmt, Signed):
            return Signed
        else:
            raise ValueError('Signedness must match.')

    def __mul__(self, other):
        point_fmt = PointFormat(self.point_fmt.point+other.point_fmt.point)

        intvals = [self.width_fmt.min * other.width_fmt.min,
                   self.width_fmt.min * other.width_fmt.max,
                   self.width_fmt.max * other.width_fmt.min,
                   self.width_fmt.max * other.width_fmt.max]
        width_fmt = self.get_width_cls(other).make(intvals)

        return Fixed(point_fmt=point_fmt, width_fmt=width_fmt)

    def __add__(self, other):
        assert self.point_fmt.point == other.point_fmt.point, "Points must be aligned"
        point_fmt = PointFormat(self.point_fmt.point)

        intvals = [self.width_fmt.min + other.width_fmt.min,
                   self.width_fmt.max + other.width_fmt.max]
        width_fmt = self.get_width_cls(other).make(intvals)

        return Fixed(point_fmt=point_fmt, width_fmt=width_fmt)

    def __neg__(self):
        assert isinstance(self.width_fmt, Signed), "Value must be signed to negate."

        point_fmt = PointFormat(self.point_fmt.point)

        intvals = [-self.width_fmt.min,
                   -self.width_fmt.max]
        width_fmt = Signed.make(intvals)

        return Fixed(point_fmt=point_fmt, width_fmt=width_fmt)

    def __sub__(self, other):
        return self + (-other)

    def align_to(self, point):
        point_fmt = PointFormat(point)

        if self.point_fmt.point >= point:
            rshift = self.point_fmt.point - point
            intvals = [self.width_fmt.min >> rshift,
                       self.width_fmt.max >> rshift]
        else:
            lshift = point - self.point_fmt.point
            intvals = [self.width_fmt.min << lshift,
                       self.width_fmt.max << lshift]

        if isinstance(self.width_fmt, Unsigned):
            return Fixed(point_fmt=point_fmt, width_fmt=Unsigned.make(intvals))
        elif isinstance(self.width_fmt, Signed):
            return Fixed(point_fmt=point_fmt, width_fmt=Signed.make(intvals))
        else:
            raise Exception('Invalid signedness.')

    def intval(self, val, func=None):
        intval = self.point_fmt.intval(val=val, func=func)
        assert self.min_int <= intval <= self.max_int, "Integer value out of range."

        return intval

    def bin_str(self, val, func=None):
        intval = self.intval(val=val, func=func)
        return self.width_fmt.bin_str(intval)

    @property
    def n(self):
        return self.width_fmt.n

    @property
    def point(self):
        return self.point_fmt.point

    @property
    def res(self):
        return self.point_fmt.res

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
        return PointFormat.make(res).to_fixed(val_or_vals, width_cls)

def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    fmt1 = Fixed.make(3.23, 0.0001, Signed)
    print(fmt1.bin_str(-0.456))

    fmt2 = Fixed.make(7.89, 0.0001, Unsigned)
    print(fmt2.n, fmt2.signed().n)
    fmt2 = fmt2.signed()

    fmt3 = fmt1 + fmt2
    print(fmt3.n, fmt3.point, fmt3.min_float, fmt3.max_float)

    fmt4 = fmt1 * fmt2
    print(fmt4.n, fmt4.point, fmt4.min_float, fmt4.max_float)

    fmt5 = fmt4.align_to(PointFormat.res2point(0.1))
    print(fmt5.n, fmt5.point, fmt5.min_float, fmt5.max_float)

if __name__=='__main__':
    main()
