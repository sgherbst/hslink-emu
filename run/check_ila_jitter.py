import matplotlib.pyplot as plt
import os.path
import sys
import logging
from scipy.stats import describe
import numpy as np

from msemu.cmd import get_parser
from msemu.ila import IlaData

def stringify(array):
    return ''.join(str(elem) for elem in array)

def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    args = parser.parse_args()

    fmt_dict_file = os.path.join(args.build_dir, 'fmt_dict.json')
    ila_dir_name = os.path.join(args.data_dir, 'ila', 'steady_state')
    ila_data = IlaData(ila_dir_name=ila_dir_name, fmt_dict_file=fmt_dict_file)

    out_tx = ila_data.tx.out_tx
    out_rx = ila_data.rxp.out_rx

    print('TX clock statistics: ')
    tx_dt = np.diff(out_tx.t)
    tx_freq = 1 / np.mean(tx_dt)
    print(describe(tx_dt - 1/tx_freq))
    print('')

    print('RX clock statistics: ')
    rx_dt = np.diff(out_rx.t)
    rx_freq = 1 / np.mean(rx_dt)
    print(describe(rx_dt - 1/rx_freq))

if __name__=='__main__':
    main()
