import numpy as np
from scipy.signal import tf2ss, zpk2ss
from scipy.linalg import matrix_balance, svd, norm, expm
from numpy.linalg import inv

def my_abcd(sys):
    # get preliminary state space representation
    if len(sys)==2:
        num, den = sys
        A, B, C, D = tf2ss(num=num, den=den)
    elif len(sys)==3:
        z, p, k = sys
        A, B, C, D = zpk2ss(z=z, p=p, k=k)
    elif len(sys)==4:
        A, B, C, D = sys
    else:
        raise ValueError('Invalid system definition.')

    # balance A matrix
    # A = T * A_tilde * T^-1
    A_tilde, T = matrix_balance(A)
    T_inv = np.diag(np.reciprocal(np.diag(T)))

    # blend output matrix into dynamics matrix
    C_new = C.dot(T)
    C_norm = norm(C_new)
    C_unit = C_new/C_norm
    C_null = nullspace(C_unit)
    C_tilde = C_norm*np.vstack((C_null.T, C_unit))

    # create new dynamics matrics
    A_prime = C_tilde.dot(A_tilde).dot(inv(C_tilde))
    B_prime = C_tilde.dot(T_inv).dot(B)

    # create simplified C matrix
    C_prime = np.zeros((1,A.shape[0]))
    C_prime[0, -1] = 1

    return A_prime, B_prime, C_prime, D

def my_impulse(sys, dt, T):
    A, B, C, D = my_abcd(sys)

    # evolution matrix
    E = expm(dt*A)

    # initialization
    nt = int(np.ceil((T/dt)+1))
    t = np.zeros(nt)
    out = np.zeros(nt)
    S = np.eye(A.shape[0])

    # evaluate successive points along the impulse response
    for k in range(nt):
        t[k] = k*dt
        out[k] = C.dot(S).dot(B)
        S = E.dot(S)

    return t, out

# nullspace reference: http://scipy-cookbook.readthedocs.io/items/RankNullspace.html
def nullspace(A, atol=1e-13, rtol=0):
    """Compute an approximate basis for the nullspace of A.

    The algorithm used by this function is based on the singular value
    decomposition of `A`.

    Parameters
    ----------
    A : ndarray
        A should be at most 2-D.  A 1-D array with length k will be treated
        as a 2-D with shape (1, k)
    atol : float
        The absolute tolerance for a zero singular value.  Singular values
        smaller than `atol` are considered to be zero.
    rtol : float
        The relative tolerance.  Singular values less than rtol*smax are
        considered to be zero, where smax is the largest singular value.

    If both `atol` and `rtol` are positive, the combined tolerance is the
    maximum of the two; that is::
        tol = max(atol, rtol * smax)
    Singular values smaller than `tol` are considered to be zero.

    Return value
    ------------
    ns : ndarray
        If `A` is an array with shape (m, k), then `ns` will be an array
        with shape (k, n), where n is the estimated dimension of the
        nullspace of `A`.  The columns of `ns` are a basis for the
        nullspace; each element in numpy.dot(A, ns) will be approximately
        zero.
    """

    A = np.atleast_2d(A)
    u, s, vh = svd(A)
    tol = max(atol, rtol * s[0])
    nnz = (s >= tol).sum()
    ns = vh[nnz:].conj().T
    return ns

def main(tau=1e-9, dt=.1e-9, T=10e-9):
    import matplotlib.pyplot as plt

    t, imp = my_impulse(([1], [tau, 1]), dt=dt, T=T)
    ideal = 1/tau*np.exp(-t/tau)

    plt.plot(t, imp, t, ideal)
    plt.show()

if __name__=='__main__':
    main()