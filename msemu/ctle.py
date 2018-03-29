from numpy import convolve
import numpy as np
from math import pi
from msemu.tf import my_impulse

def db2mag(db):
    return 10.0**(db/20.0)

def get_ctle_imp(dt, T, fp1=2e9, fp2=8e9, db=-4):
    # angular frequency conversion
    wp1 = 2*pi*fp1
    wp2 = 2*pi*fp2

    # numerator and denominator of transfer function
    gdc = db2mag(db)
    num = gdc*np.array([1/(gdc*wp1), 1])
    den = convolve(np.array([1/wp1, 1]), np.array([1/wp2, 1]))
    
    # compute impulse response of CTLE
    # done with custom code due to issues with tf2ss and impulse
    ctle_imp = my_impulse(sys=(num, den), dt=dt, T=T)

    return ctle_imp

def main(dt=.1e-12, T=10e-9):
    import matplotlib.pyplot as plt

    t, imp = get_ctle_imp(dt=dt, T=T)

    plt.plot(t, imp)
    plt.show()

if __name__=='__main__':
    main()