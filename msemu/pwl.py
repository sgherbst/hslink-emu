from numpy import genfromtxt, convolve
import matplotlib.pyplot as plt
import argparse
import numpy as np
from scipy.signal import lsim, impulse, tf2ss, fftconvolve
from scipy.interpolate import interp1d
from scipy.stats import describe
import scipy.sparse
from math import exp, log, ceil, floor, pi, log2, sqrt
import subprocess
from scipy.linalg import matrix_balance, svd, norm, expm, lstsq
from numpy.linalg import lstsq, solve, inv
import cvxpy
import logging, sys

class PWL:
    def __init__(self, offsets, slopes, times, dtau):
        self.offsets = offsets
        self.slopes = slopes
        self.times = times
        self.dtau = dtau

    def eval(self, pts):
        idx = np.floor((pts-self.times[0])/self.dtau).astype(int)
        return self.offsets[idx] + self.slopes[idx]*(pts-self.times[idx])

class Waveform:
    def __init__(self, t, v):
        # store arguments
        self.t = t
        self.v = v

    def make_pwl(self, n, start=None, stop=None):
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
        rows = np.zeros(2*nchk)
        cols = np.zeros(2*nchk)
        data = np.zeros(2*nchk)

        for k in range(nchk):
            # time of point to check
            tchk = self.t[k+idx_min]

            # index of associated PWL control point
            idx_float = (tchk - times[0])/dtau
            idx_int = np.floor(idx_float).astype(int)

            # linear correction term
            alpha = idx_float - idx_int

            # contribution from control point idx_int
            rows[2*k+0] = k
            cols[2*k+0] = idx_int
            data[2*k+0] = 1 - alpha

            # contribution from control point idx_int+1
            rows[2*k+1] = k
            cols[2*k+1] = idx_int+1
            data[2*k+1] = alpha

        # construct the optimization problem
        A = scipy.sparse.coo_matrix((data, (rows, cols)), shape=(nchk, n+1))
        A = cvxpy.Constant(A)

        b = self.v[idx_min:(idx_max+1)]

        # run optimization
        x = cvxpy.Variable(n+1)
        objective = cvxpy.Minimize(cvxpy.pnorm(A * x - b, p=float('inf')))
        prob = cvxpy.Problem(objective)
        result = prob.solve()
        logging.debug('Maximum PWL fit error: {}'.format(result))

        value = np.squeeze(np.asarray(x.value))
        offsets = value[:-1]
        slopes = np.diff(value)/dtau

        return PWL(offsets=offsets, slopes=slopes, times=times, dtau=dtau)

def main():
    #logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    t = np.linspace(0, 3, 10e3)
    v = np.exp(t)

    wave = Waveform(t, v)
    pwl = wave.make_pwl(16)

    plt.plot(t, v, t[:-1], pwl.eval(t[:-1]))
    plt.show()
    
if __name__=='__main__':
    main()
