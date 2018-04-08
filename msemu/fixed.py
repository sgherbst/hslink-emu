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
    # constructor

    def __init__(self, n, signed, min=None, max=None):
        assert isinstance(n, int)
        self._n = n

        self._signed = signed

        if min is not None:
            assert isinstance(min, int)
            assert min >= self.abs_min
            self._min = min
        else:
            self._min = self.abs_min

        if max is not None:
            assert isinstance(max, int)
            assert max <= self.abs_max
            self._max = max
        else:
            self._max = self.abs_max

    # properties

    @property
    def n(self):
        return self._n

    @property
    def signed(self):
        return self._signed

    @property
    def unsigned(self):
        return not self.signed

    @property
    def abs_min(self):
        if self.signed:
            return -(1<<(self.n-1))
        else:
            return 0

    @property
    def abs_max(self):
        if self.signed:
            return (1<<(self.n-1))-1
        else:
            return (1<<self.n)-1

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    # member functions

    def bin_str(self, val_or_vals):
        vals = listify(val_or_vals)
        bin_strs = []

        for val in vals:
            assert isinstance(val, int)
            assert self.min <= val <= self.max

            if val < 0:
                unsigned_val = (1<<self.n) + val
            else:
                unsigned_val = val

            str_val = format(unsigned_val, '0' + str(self.n) + 'b')
            assert len(str_val) == self.n

            bin_strs.append(str_val)

        if isinstance(val_or_vals, collections.Iterable):
            return bin_strs
        else:
            assert len(bin_strs)==1
            return bin_strs[0]

    def to_signed(self):
        return WidthFormat.make([self.min, self.max], signed=True)

    def to_unsigned(self):
        return WidthFormat.make([self.min, self.max], signed=False)

    # static methods

    @staticmethod
    def width(val_or_vals, signed):
        vals = listify(val_or_vals)

        widths = []
        for val in vals:
            assert isinstance(val, int), 'Values must be integers.'

            if signed:
                if val < 0:
                    width = int(ceil(1+log2(-val)))
                else:
                    width = int(ceil(1+log2(val+1)))
            else:
                assert val >= 0, 'Unsigned values must be non-negative.'
                width = int(ceil(log2(val+1)))

            widths.append(width)

        if isinstance(val_or_vals, collections.Iterable):
            return widths
        else:
            assert len(widths)==1
            return widths[0]

    @staticmethod
    def make(val_or_vals, signed):
        vals = listify(val_or_vals)
        return WidthFormat(n=max(WidthFormat.width(vals, signed=signed)),
                           min=min(vals), max=max(vals), signed=signed)

    # operator overloading

    def __add__(self, other):
        intvals = [self.min + other.min, self.max + other.max]

        if self.unsigned and other.unsigned:
            return WidthFormat.make(intvals, signed=False)
        elif self.signed and other.signed:
            return WidthFormat.make(intvals, signed=True)
        else:
            raise ValueError('Signedness must match.')

    def __sub__(self, other):
        intvals = [self.min - other.max, self.max - other.min]

        if self.unsigned and other.unsigned:
            return WidthFormat.make(intvals, signed=False)
        elif self.signed and other.signed:
            return WidthFormat.make(intvals, signed=True)
        else:
            raise ValueError('Signedness must match.')

    def __neg__(self):
        return WidthFormat.make([-self.min, -self.max], signed=self.signed)

    def __mul__(self, other):
        intvals = [self.min * other.min,
                   self.min * other.max,
                   self.max * other.min,
                   self.max * other.max]

        if self.unsigned and other.unsigned:
            return WidthFormat.make(intvals, signed=False)
        elif self.signed and other.signed:
            return WidthFormat.make(intvals, signed=True)
        else:
            raise ValueError('Signedness must match.')

    def __rshift__(self, shift):
        intvals = [self.min >> shift,
                   self.max >> shift]
        return WidthFormat.make(intvals, signed=self.signed)

    def __lshift__(self, shift):
        intvals = [self.min << shift,
                   self.max << shift]
        return WidthFormat.make(intvals, signed=self.signed)

class PointFormat:
    # constructor

    def __init__(self, point):
        self.point = point

    # properties

    @property
    def res(self):
        return PointFormat.point2res(self.point)

    # member functions

    def intval(self, val_or_vals, func=None):
        if func is None:
            func = round
        return PointFormat.float2int(val_or_vals, point=self.point, func=func)

    def to_fixed(self, val_or_vals, signed):
        vals = listify(val_or_vals)

        min_float = min(vals)
        max_float = max(vals)

        min_intval = self.intval(min_float, func=floor)
        max_intval = self.intval(max_float, func=ceil)

        point_fmt = PointFormat(self.point)
        width_fmt = WidthFormat.make([min_intval, max_intval], signed=signed)

        return Fixed(point_fmt=point_fmt, width_fmt=width_fmt)

    # static methods

    @staticmethod
    def res2point(res):
        return int(ceil(-log2(res)))

    @staticmethod
    def point2res(point):
        return 2.0 ** (-point)

    @staticmethod
    def float2int(val_or_vals, point, func):
        vals = listify(val_or_vals)
        res =  PointFormat.point2res(point)
        scaled_floats = [val/res for val in vals]

        intvals = [int(func(scaled_float)) for scaled_float in scaled_floats]
        assert all(isinstance(intval, int) for intval in intvals)

        if isinstance(val_or_vals, collections.Iterable):
            return intvals
        else:
            assert len(intvals)==1
            return intvals[0]

    @staticmethod
    def make(res):
        point = PointFormat.res2point(res)
        return PointFormat(point=point)

    # operator overloading

    def __add__(self, other):
        assert self.point == other.point, 'Points must be aligned.'
        return self

    def __sub__(self, other):
        assert self.point == other.point, 'Points must be aligned.'
        return self

    def __neg__(self):
        return self

    def __mul__(self, other):
        return PointFormat(self.point+other.point)

class Fixed:
    # constructor

    def __init__(self, point_fmt, width_fmt):
        self.point_fmt = point_fmt
        self.width_fmt = width_fmt

    # properties

    @property
    def signed(self):
        return self.width_fmt.signed

    @property
    def unsigned(self):
        return self.width_fmt.unsigned

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

    # member functions

    def to_signed(self):
        return Fixed(point_fmt=self.point_fmt, width_fmt=self.width_fmt.to_signed())

    def to_unsigned(self):
        return Fixed(point_fmt=self.point_fmt, width_fmt=self.width_fmt.to_unsigned())

    def align_to(self, point):
        point_fmt = PointFormat(point)

        if self.point_fmt.point >= point:
            rshift = self.point_fmt.point - point
            width_fmt = self.width_fmt >> rshift
        else:
            lshift = point - self.point_fmt.point
            width_fmt = self.width_fmt << lshift

        return Fixed(point_fmt=point_fmt, width_fmt=width_fmt)

    def intval(self, val_or_vals, func=None):
        vals = listify(val_or_vals)

        intvals = self.point_fmt.intval(vals, func=func)
        assert all(self.min_int <= intval <= self.max_int for intval in intvals)

        if isinstance(val_or_vals, collections.Iterable):
            return intvals
        else:
            assert len(intvals) == 1
            return intvals[0]

    def bin_str(self, val_or_vals, func=None):
        vals = listify(val_or_vals)

        intvals = self.intval(vals, func=func)
        bin_strs = self.width_fmt.bin_str(intvals)

        if isinstance(val_or_vals, collections.Iterable):
            return bin_strs
        else:
            assert len(bin_strs) == 1
            return bin_strs[0]

    # static methods

    @staticmethod
    def make(val_or_vals, res, signed):
        return PointFormat.make(res).to_fixed(val_or_vals, signed=signed)

    @staticmethod
    def cover(formats_iterable):
        assert isinstance(formats_iterable, collections.Iterable)
        formats = list(formats_iterable)

        # input checking
        assert all(format.point==formats[0].point for format in formats[1:])
        assert all(format.signed == formats[0].signed for format in formats[1:])

        # find minimum and maximum integers that need to be represented
        min_int = min(format.min_int for format in formats)
        max_int = max(format.max_int for format in formats)

        # make a format that can represent all of those integers
        return Fixed(point_fmt=formats[0].point_fmt,
                     width_fmt=WidthFormat.make([min_int, max_int], signed=formats[0].signed))

    # operator overloading

    def __add__(self, other):
        return Fixed(point_fmt=self.point_fmt+other.point_fmt,
                     width_fmt=self.width_fmt+other.width_fmt)

    def __radd__(self, other):
        # only here so that sum function will work...
        if other == 0:
            return self
        else:
            raise Exception('other must not be 0 or a Fixed type...')

    def __sub__(self, other):
        return Fixed(point_fmt=self.point_fmt-other.point_fmt,
                     width_fmt=self.width_fmt-other.width_fmt)

    def __neg__(self):
        return Fixed(point_fmt=-self.point_fmt,
                     width_fmt=-self.width_fmt)

    def __mul__(self, other):
        return Fixed(point_fmt=self.point_fmt*other.point_fmt,
                     width_fmt=self.width_fmt*other.width_fmt)

def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    fmt1 = Fixed.make((-3.23, 3.23), 0.0001, signed=True)
    print(fmt1.bin_str(-0.456))

    fmt2 = Fixed.make(7.89, 0.0001, signed=False)
    print(fmt2.n, fmt2.to_signed().n)
    fmt2 = fmt2.to_signed()

    fmt3 = fmt1 + fmt2
    print(fmt3.n, fmt3.point, fmt3.min_float, fmt3.max_float)

    fmt4 = fmt1 * fmt2
    print(fmt4.n, fmt4.point, fmt4.min_float, fmt4.max_float)

    fmt5 = fmt4.align_to(PointFormat.res2point(0.1))
    print(fmt5.n, fmt5.point, fmt5.min_float, fmt5.max_float)

    fmt6 = Fixed.make([1,3], 0.001, signed=False)
    fmt7 = fmt6.point_fmt.to_fixed([0, 1], signed=False)
    fmt8 = fmt6-fmt7
    print(fmt8.min_float, fmt8.max_float)

if __name__=='__main__':
    main()