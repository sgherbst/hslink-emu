from numpy import genfromtxt
import numpy as np
import os.path
import json

from msemu.pwl import Waveform
from msemu.fixed import Fixed

class RxpData:
    def __init__(self, filter_out, comp_in, dco_code, out_rx):
        self.filter_out = filter_out
        self.comp_in = comp_in
        self.dco_code = dco_code
        self.out_rx = out_rx

    @staticmethod
    def make(data_file, out_fmt, comp_fmt, time_fmt):
        with open(data_file, 'r') as f:
            header = f.readline()
        col_dict = parse_ila_header(header)

        data = genfromtxt(data_file, delimiter=',', skip_header=1, autostrip=True, dtype=int)

        t = data[:, col_dict['time_curr_1']] * time_fmt.res

        v_filter_out = data[:, col_dict['filter_out_1']] * out_fmt.res
        v_comp_in = data[:, col_dict['comp_in']] * comp_fmt.res
        v_dco_code = data[:, col_dict['dco_code']]
        v_out_rx = data[:, col_dict['out_rx']]

        return RxpData(filter_out=Waveform(t=t, v=v_filter_out),
                       comp_in=Waveform(t=t, v=v_comp_in),
                       dco_code=Waveform(t=t, v=v_dco_code),
                       out_rx=Waveform(t=t, v=v_out_rx))

class RxnData:
    def __init__(self, filter_out):
        self.filter_out = filter_out

    @staticmethod
    def make(data_file, out_fmt, time_fmt):
        with open(data_file, 'r') as f:
            header = f.readline()
        col_dict = parse_ila_header(header)

        data = genfromtxt(data_file, delimiter=',', skip_header=1, autostrip=True, dtype=int)

        t = data[:, col_dict['time_curr_2']] * time_fmt.res
        v = data[:, col_dict['filter_out']]*out_fmt.res

        return RxnData(filter_out=Waveform(t=t, v=v))

class TxData:
    def __init__(self, filter_in, out_tx):
        self.filter_in = filter_in
        self.out_tx = out_tx

    @staticmethod
    def make(data_file, in_fmt, time_fmt):
        with open(data_file, 'r') as f:
            header = f.readline()
        col_dict = parse_ila_header(header)

        data = genfromtxt(data_file, delimiter=',', skip_header=1, autostrip=True, dtype=int)

        # read time-value pair
        t = data[:, col_dict['time_curr']] * time_fmt.res
        v_filter_in = data[:, col_dict['filter_in']] * in_fmt.res
        v_out_tx = data[:, col_dict['out_tx']]

        # return waveform
        return TxData(filter_in = Waveform(t=np.concatenate(([0], t[:-1])), v=v_filter_in),
                      out_tx = Waveform(t=t, v=v_out_tx))

def parse_ila_header(header):
    # split header into column names
    cols = [col.strip() for col in header.strip().split(',')]

    # map column name to index
    # the width of signals is removed to make this
    # more flexible
    col_dict = {}
    for idx, col in enumerate(cols):
        if '[' in col:
            key = col[:col.index('[')]
        else:
            key = col

        col_dict[key] = idx

    return col_dict

class IlaData:
    def __init__(self, ila_dir_name, fmt_dict_file):
        # get data formats
        with open(fmt_dict_file) as f:
            fmt_dict = json.loads(f.read())

        self.in_fmt = Fixed.from_dict(fmt_dict['in_fmt'])
        self.out_fmt = Fixed.from_dict(fmt_dict['out_fmt'])
        self.comp_fmt = Fixed.from_dict(fmt_dict['comp_fmt'])
        self.time_fmt = Fixed.from_dict(fmt_dict['time_fmt'])

        tx_file = os.path.join(ila_dir_name, 'ila_0_data.csv')
        rx_p_file = os.path.join(ila_dir_name, 'ila_1_data.csv')
        rx_n_file = os.path.join(ila_dir_name, 'ila_2_data.csv')

        if os.path.isfile(tx_file):
            self.tx = TxData.make(tx_file, in_fmt=self.in_fmt, time_fmt=self.time_fmt)
        else:
            self.tx = None

        if os.path.isfile(rx_p_file):
            self.rxp = RxpData.make(rx_p_file, out_fmt=self.out_fmt, comp_fmt=self.comp_fmt, time_fmt=self.time_fmt)
        else:
            self.rxp = None

        if os.path.isfile(rx_n_file):
            self.rxn = RxnData.make(rx_n_file, out_fmt=self.out_fmt, time_fmt=self.time_fmt)
        else:
            self.rxn = None
