import matplotlib.pyplot as plt
import numpy as np
from msemu.server import get_client
from argparse import ArgumentParser

def main(filename='../data/iladata.csv', time_exponent=-47):
    # read in command-line arguments
    parser = ArgumentParser()
    parser.add_argument('--dco_init', type=int, default=1000)
    parser.add_argument('--ki_lf', type=int, default=8)
    parser.add_argument('--kp_lf', type=int, default=256)
    args = parser.parse_args()

    # connect to the server
    s = get_client()

    # set up configuration
    s.set_vio('dco_init', str(args.dco_init))
    s.set_vio('ki_lf', str(args.ki_lf))
    s.set_vio('kp_lf', str(args.kp_lf))

    # run the emulation
    s.sendline('source emu_dco.tcl')

    # read the data
    with open (filename, 'r') as f:
        header = f.readline()

    for k, col in enumerate(header.split(',')):
        if col.strip().startswith('time_curr_2'):
            time_curr_2 = k
        elif col.strip().startswith('dco_code'):
            dco_code = k

    data = np.genfromtxt(filename, skip_header=1, usecols=(time_curr_2, dco_code), delimiter=',', dtype='long')

    t = data[:, 0]*(2**time_exponent)
    codes = data[:, 1]

    plt.plot(t*1e6, codes)
    plt.xlabel('Time (us)')
    plt.ylabel('DCO Code')
    plt.show()

if __name__ == '__main__':
    main()