import numpy as np
import logging, sys
from math import ceil, floor
from scipy.interpolate import interp1d
import cvxpy

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

    def trim(self, n):
        assert n <= self.n
        return Waveform(t=self.t[:n], v=self.v[:n])

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

    def make_pwl(self, times, n_check=1000):
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
        v_check = interp1d(self.t, self.v)(t_check)

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
        error = prob.solve()

        # compute PWL respresentation
        v_ctrl = np.array(x.value).flatten()
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
