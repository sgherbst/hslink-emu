import matplotlib.pyplot as plt
import os.path
import sys
import logging

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

    out_tx_str = stringify(out_tx.v)
    out_rx_str = stringify(out_rx.v)

    print('Running loopback test...')
    idx = out_rx_str.index(out_tx_str)
    assert idx >= 0, 'Loopback test failed :-('

    print('Loopback test passed :-)')
    delay = out_rx.t[idx] - out_tx.t[0]

    print('TX-RX skew: {:0.3f} ns'.format(1e9*delay))

if __name__=='__main__':
    main()
