import matplotlib.pyplot as plt
import numpy as np
from msemu.server import get_client

def main(filename='../data/iladata.csv'):
    # run the command
    s = get_client()
    print(s.sendline('source emu_dco.tcl'), end='')

    # read the data
    with open (filename, 'r') as f:
        header = f.readline()

    for k, col in enumerate(header.split(',')):
        if col.strip().startswith('time_curr_2'):
            time_curr_2 = k
        elif col.strip().startswith('dco_code'):
            dco_code = k

    data = np.genfromtxt(filename, skip_header=1, usecols=(time_curr_2, dco_code), delimiter=',', dtype='long')

    t = data[:, 0]*(2**-47) # TODO: avoid hardcoding the exponent
    codes = data[:, 1]

    plt.plot(t*1e6, codes)
    plt.xlabel('Time (us)')
    plt.ylabel('DCO Code')
    plt.show()

if __name__ == '__main__':
    main()