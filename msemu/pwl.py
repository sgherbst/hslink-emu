import numpy as np
import scipy.sparse
import cvxpy
import logging, sys

class PWL:
    def __init__(self, offsets, slopes, times, dtau):
        self.times = times
        self.dtau = dtau

        assert len(offsets) == self.n
        self.offsets = offsets

        assert len(slopes) == self.n
        self.slopes = slopes

    @property
    def n(self):
        return len(self.times)

    def domain(self, dt):
        return np.arange(self.times[0], self.times[-1], dt)

    def eval(self, pts):
        idx = np.floor((pts-self.times[0])/self.dtau).astype(int)
        return self.offsets[idx] + self.slopes[idx]*(pts-self.times[idx])

    def to_fixed_table(self, offset_fmt, slope_fmt, bias=0):
        retval = ''

        for offset, slope in zip(self.offsets, self.slopes):
            retval += offset_fmt.bin_str(offset-bias) + slope_fmt.bin_str(slope) + '\n'

        return retval

class Waveform:
    def __init__(self, t, v):
        # store arguments
        self.t = t
        self.v = v

    def make_pwl(self, start=None, stop=None, n=50):
        # assign start and stop points of representation if not given
        if start is None:
            start = self.t[0]
        if stop is None:
            stop = self.t[-1]

        # check representation
        assert start >= self.t[ 0]
        assert stop  <= self.t[-1]

        # store segment start times
        times, dtau = np.linspace(start, stop, n+1, retstep=True)

        # find the relevant test points
        idx_min = np.searchsorted(self.t, start)
        idx_max = np.searchsorted(self.t, stop)-1

        # set up matrix for optimization problem
        nchk = idx_max-idx_min+1
        A = scipy.sparse.dok_matrix((nchk, n+1), dtype=np.float64)

        # used to make sure no control points are skipped
        last_idx_int = -1

        for k in range(nchk):
            # time of point to check
            tchk = self.t[k+idx_min]

            # index of associated PWL control point
            idx_float = (tchk - times[0])/dtau
            idx_int = np.floor(idx_float).astype(int)

            # check to ensure no control points are skipped
            assert (idx_int - last_idx_int) <= 1

            # linear correction term
            alpha = idx_float - idx_int

            A[k, idx_int] = 1 - alpha
            A[k, idx_int+1] = alpha

            # update history of control points
            last_idx_int = idx_int

        # construct the optimization problem
        A = cvxpy.Constant(A)
        b = self.v[idx_min:(idx_max+1)]

        # run optimization
        x = cvxpy.Variable(n+1)
        objective = cvxpy.Minimize(cvxpy.pnorm(A*x - b, p=float('inf')))
        prob = cvxpy.Problem(objective)
        result = prob.solve()

        logging.debug('Maximum PWL fit error: {}'.format(result))

        values = np.squeeze(np.asarray(x.value))
        offsets = values[:-1]
        slopes = np.diff(values)/dtau

        return PWL(offsets=offsets, slopes=slopes, times=times[:-1], dtau=dtau)

def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    t = np.linspace(0, 3, 1e3)
    v = np.exp(t)

    wave = Waveform(t, v)
    pwl = wave.make_pwl(0.5, 2.5, 4)

    from msemu.fixed import FixedSigned
    fmt = FixedSigned.get_format(10, 0.001)

    print('PWL Table')
    print('Size: {} bits'.format(pwl.n*(fmt.n+fmt.n)))
    print(pwl.to_fixed_table(fmt, fmt))

    import matplotlib.pyplot as plt
    t_eval = pwl.domain(0.01)
    plt.plot(t, v, t_eval, pwl.eval(t_eval))
    plt.show()

if __name__=='__main__':
    main()