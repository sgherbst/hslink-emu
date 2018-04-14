import numpy as np
import logging, sys
from math import ceil, floor, log2
from scipy.interpolate import interp1d
import cvxpy

from msemu.fixed import Fixed, WidthFormat

class PwlTable:
    def __init__(self, pwls, high_bits_fmt, low_bits_fmt, addr_offset_int, offset_point_fmt, slope_point_fmt):
        # save settings
        self.pwls = pwls
        self.high_bits_fmt = high_bits_fmt
        self.low_bits_fmt = low_bits_fmt
        self.addr_offset_int = addr_offset_int
        self.offset_point_fmt = offset_point_fmt
        self.slope_point_fmt = slope_point_fmt

        # check input validity
        assert all(np.isclose(pwl.dtau, self.high_bits_fmt.res) for pwl in self.pwls)

        # set up the format of the ROM
        self.set_rom_fmt()

    @property
    def n_segments(self):
        n_segments_0 = self.pwls[0].n
        assert all(pwl.n == n_segments_0 for pwl in self.pwls)
        return n_segments_0

    @property
    def n_settings(self):
        return len(self.pwls)

    @property
    def setting_bits(self):
        return int(ceil(log2(self.n_settings)))

    @property
    def setting_padding(self):
        return ((1<<self.setting_bits)-self.n_settings)

    def set_rom_fmt(self):
        # determine the bias
        bias_floats = [(min(pwl.offsets)+max(pwl.offsets))/2 for pwl in self.pwls]
        self.bias_ints = self.offset_point_fmt.intval(bias_floats)
        bias_fmts = [Fixed(point_fmt=self.offset_point_fmt,
                           width_fmt=WidthFormat.make(bias_int, signed=True))
                     for bias_int in self.bias_ints]
        self.bias_fmt = Fixed.cover(bias_fmts)

        # determine offset representation
        offset_floats = [[offset - bias_float for offset in pwl.offsets]
                         for pwl, bias_float in zip(self.pwls, bias_floats)]
        self.offset_ints = [self.offset_point_fmt.intval(setting)
                            for setting in offset_floats]
        offset_fmts = [[Fixed(point_fmt=self.offset_point_fmt,
                              width_fmt=WidthFormat.make(offset_int, signed=True))
                        for offset_int in setting]
                       for setting in self.offset_ints]
        self.offset_fmt = Fixed.cover(Fixed.cover(setting) for setting in offset_fmts)

        # determine slope representation
        self.slope_ints = [self.slope_point_fmt.intval(pwl.slopes)
                           for pwl in self.pwls]
        slope_fmts = [[Fixed(point_fmt=self.slope_point_fmt,
                             width_fmt=WidthFormat.make(slope_int, signed=True))
                       for slope_int in setting]
                      for setting in self.slope_ints]
        self.slope_fmt = Fixed.cover(Fixed.cover(setting) for setting in slope_fmts)

        # determine output representation of output
        out_fmts = []

        for setting in range(self.n_settings):
            for offset_fmt, slope_fmt in zip(offset_fmts[setting],
                                             slope_fmts[setting]):
                out_fmts.append(bias_fmts[setting]
                                + offset_fmt
                                + (slope_fmt * self.low_bits_fmt.to_signed()).align_to(self.offset_point_fmt.point))

        self.out_fmt = Fixed.cover(out_fmts)

    def write_segment_table(self, fname):
        with open(fname, 'w') as f:
            # write the segment tables for each setting one after another
            for offset_setting, slope_setting in zip(self.offset_ints, self.slope_ints):
                offset_strs = self.offset_fmt.width_fmt.bin_str(offset_setting)
                slope_strs = self.slope_fmt.width_fmt.bin_str(slope_setting)
                for offset_str, slope_str in zip(offset_strs, slope_strs):
                    f.write(offset_str+slope_str+'\n')

            # pad the end with zeros as necessary
            zero_str = '0'*(self.offset_fmt.n+self.slope_fmt.n)
            for i in range(self.setting_padding):
                for j in range(self.n_segments):
                    f.write(zero_str+'\n')

    def write_bias_table(self, fname):
        with open(fname, 'w') as f:
            # write the bias values into a table
            for bias_str in self.bias_fmt.width_fmt.bin_str(self.bias_ints):
                f.write(bias_str + '\n')

            # pad the end with zeros as necessary
            zero_str = '0'*self.bias_fmt.n
            for i in range(self.setting_padding):
                f.write(zero_str+'\n')

    @property
    def table_size_bits(self):
        return self.n_settings * self.n_segments * (self.offset_fmt.n + self.slope_fmt.n)

class PWL:
    def __init__(self, offsets, slopes, times, error):
        self.times = times
        self.error = error

        self.dtau = Waveform.get_dt(self.times)

        assert len(offsets) == self.n
        self.offsets = offsets

        assert len(slopes) == self.n
        self.slopes = slopes

    @property
    def n(self):
        return len(self.times)

    def domain(self, dt):
        return np.arange(self.times[0], self.times[-1]+self.dtau, dt)

    def eval(self, pts):
        idx = np.floor((pts-self.times[0])/self.dtau).astype(int)
        return self.offsets[idx] + self.slopes[idx]*(pts-self.times[idx])

class Waveform:
    def __init__(self, t, v):
        # store time vector
        self.t = t

        # store value vector
        assert len(v)==self.n
        self.v = v

        # placeholder for memoized value
        self._dt = None

    @property
    def dt(self):
        if self._dt is None:
            self._dt = Waveform.get_dt(self.t)
        return self._dt

    def trim(self, n):
        assert n <= self.n
        return Waveform(t=self.t[:n], v=self.v[:n])

    def start_after(self, t0):
        idx = np.argmax(self.t >= t0)
        assert self.t[idx] >= t0

        return Waveform(t=self.t[idx:], v=self.v[idx:])

    def save(self, file_name):
        arr = np.column_stack((self.t, self.v))
        np.save(file_name, arr)

    @staticmethod
    def load(file_name):
        arr = np.load(file_name)
        return Waveform(t=arr[:, 0], v=arr[:, 1])

    @staticmethod
    def get_dt(t):
        time_diffs = np.diff(t)
        dt = np.median(time_diffs)
        assert np.all(np.isclose(time_diffs, dt * np.ones(len(time_diffs))))

        return dt

    @property
    def n(self):
        return len(self.t)

    @property
    def yss(self):
        return self.v[-1]

    def find_settled_time(self, thresh=0.01):
        # find end of step
        err = np.abs(self.v - self.yss)/self.yss
        idx_settled = len(err) - 1 - np.argmax(err[::-1] > thresh)
        assert err[idx_settled] > thresh
        assert err[idx_settled + 1] <= thresh

        return self.t[idx_settled]

    def make_pwl(self, times, n_check=1000, v_scale_factor=1):
        # add one last point at the end
        dtau = Waveform.get_dt(times)
        t_ctrl = np.concatenate((times, [times[-1]+dtau]))
        t_start = t_ctrl[0]
        t_stop = t_ctrl[-1]

        # check that the waveform is represented at the times required
        assert t_start >= self.t[0], '{} !>= {}'.format(t_start, self.t[0])
        assert t_stop <= self.t[-1], '{} !<= {}'.format(t_stop, self.t[-1])
        assert n_check >= len(t_ctrl)

        # points at which error will be checked
        t_check = np.linspace(t_start, t_stop, n_check)
        v_check = interp1d(self.t, self.v/v_scale_factor)(t_check)

        # compute control points
        A = np.zeros((n_check, len(t_ctrl)))
        for k in range(n_check):
            idx_float = (t_check[k] - t_ctrl[0]) / dtau
            idx_int = int(floor(idx_float))
            alpha = idx_float - idx_int
            if 0 <= idx_int < len(t_ctrl) - 1:
                A[k, idx_int] = 1 - alpha
                A[k, idx_int+1] = alpha
            elif idx_int == len(t_ctrl) - 1:
                A[k, idx_int] = 1
            else:
                raise Exception('Invalid index.')

        # run optimization
        x = cvxpy.Variable(len(t_ctrl))
        obj = cvxpy.Minimize(cvxpy.pnorm(A*x - v_check, p=float('inf')))
        prob = cvxpy.Problem(obj)
        error = prob.solve()*v_scale_factor

        # compute PWL respresentation
        v_ctrl = np.array(x.value).flatten()*v_scale_factor
        offsets = v_ctrl[:-1]
        slopes = np.diff(v_ctrl)/dtau

        return PWL(offsets=offsets, slopes=slopes, times=times, error=error)

def main(tau=1e-9):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    t = np.linspace(0, 3*tau, 1e3)
    v = np.exp(t/tau)

    wave = Waveform(t=t, v=v)
    times = (0.5+0.5*np.arange(4))*tau
    pwl = wave.make_pwl(times=times)
    print(pwl.offsets)
    print(pwl.slopes)

    import matplotlib.pyplot as plt
    t_eval = pwl.domain(0.01*tau)
    plt.plot(t, v, t_eval, pwl.eval(t_eval))
    plt.show()

if __name__=='__main__':
    main()
