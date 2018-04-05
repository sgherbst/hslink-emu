import numpy as np
import logging, sys
from math import ceil
from scipy.interpolate import interp1d

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

        # get time spacing
        self.dt = Waveform.get_dt(self.t)

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

    def find_stop_idx(self, thresh=0.01):
        # find end of step
        err = np.abs(self.v - self.yss)/self.yss
        idx_stop = len(err) - 1 - np.argmax(err[::-1] > thresh)
        assert err[idx_stop] > thresh
        assert err[idx_stop + 1] <= thresh

        return idx_stop

    def trim_through_idx(self, idx_stop):
        t_new = self.t[:idx_stop + 1]
        v_new = self.v[:idx_stop + 1]
        return Waveform(t=t_new, v=v_new)

    def trim_settling(self, thresh=0.01):
        idx_stop = self.find_stop_idx(thresh=thresh)
        return self.trim_through_idx(idx_stop=idx_stop)

    def extend(self, Tmax):
        # check if extension is necessary
        if Tmax <= self.t[-1]:
            return Waveform(t=self.t, v=self.v)

        # check if the step has to be extended
        n_new = int(ceil(Tmax / self.dt)) + 1

        # fill the end
        t_ext = np.arange(self.n, n_new) * self.dt
        v_ext = np.ones(n_new - self.n) * self.v[-1]

        t_new = np.concatenate((self.t, t_ext))
        v_new = np.concatenate((self.v, v_ext))
        return Waveform(t=t_new, v=v_new)

    def make_pwl(self, times):
        # add one last point at the end
        dtau = Waveform.get_dt(times)
        times_plus_end = np.concatenate((times, [times[-1]+dtau]))
        t_start = times_plus_end[0]
        t_stop = times_plus_end[-1]

        # check that the waveform is represented at the times required
        assert t_start >= self.t[0], '{} !>= {}'.format(t_start, self.t[0])
        assert t_stop <= self.t[-1], '{} !<= {}'.format(t_stop, self.t[-1])

        # compute control points
        values = interp1d(self.t, self.v)(times_plus_end)

        # points at which error will be checked
        idx_min = np.searchsorted(self.t, t_start)
        idx_max = np.searchsorted(self.t, t_stop)-1

        # check error
        resid = interp1d(times_plus_end, values)(self.t[idx_min:idx_max+1]) - self.v[idx_min:idx_max+1]
        error = np.max(np.abs(resid))
        logging.debug('PWL error: {}'.format(error))

        # compute PWL respresentation
        offsets = values[:-1]
        slopes = np.diff(values)/dtau

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