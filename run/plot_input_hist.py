import matplotlib.pyplot as plt
import os.path
import sys
import logging
import numpy as np

from msemu.cmd import get_parser
from msemu.ila import IlaData
from msemu.pwl import Waveform

def bimode(data):
    pos_data = data[data>0]
    neg_data = data[data<0]

    mu_1 = np.mean(pos_data)
    mu_2 = np.mean(neg_data)

    sigma_1 = np.std(pos_data)
    sigma_2 = np.std(neg_data)

    return mu_1, mu_2, sigma_1, sigma_2

def find_sigma(data):
    pos_data = data[data>0]
    neg_data = data[data<0]

    mu_1 = np.mean(pos_data)
    mu_2 = np.mean(neg_data)

    pos_err = pos_data-mu_1
    neg_err = neg_data-mu_2
    err = np.concatenate((pos_err, neg_err))

    return np.std(err)

def dist(x, mu, sigma):
    return ((1 / (np.sqrt(2 * np.pi) * sigma)) *
     np.exp(-0.5 * (1 / sigma * (x - mu)) ** 2))

def main(fmts=['png', 'pdf', 'eps']):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = get_parser()
    parser.add_argument('--trim', type=float, default=1e-6, help='Amount of time to trim from beginning of waveforms.')
    args = parser.parse_args()

    fig, ax = plt.subplots()

    # Emulator
    fmt_dict_file = os.path.join(args.build_dir, 'fmt_dict.json')
    ila_dir_name = os.path.join(args.data_dir, 'ila', 'steady_state')
    ila_data = IlaData(ila_dir_name=ila_dir_name, fmt_dict_file=fmt_dict_file)
    comp_in = ila_data.rxp.comp_in.start_after(args.trim)
    emu_data = comp_in.v

    sigma_em = find_sigma(emu_data)
    print('FPGA Sigma: {:0.1f} mV'.format(1e3*sigma_em))

    ax.hist(emu_data, 100, normed=1, facecolor='forestgreen', alpha=0.8, label='FPGA')

    # Simulator
    mat = np.load(os.path.join(args.data_dir, 'SteadyStatePySim.npy'))
    cpu_t =  mat[:, 0]
    cpu_v = mat[:, 3]
    cpu_wave = Waveform(t=cpu_t, v=cpu_v)
    cpu_wave = cpu_wave.start_after(args.trim)
    sim_data = cpu_wave.v

    sigma_cpu = find_sigma(sim_data)
    print('CPU Sigma: {:0.1f} mV'.format(1e3 * sigma_cpu))

    mu_cpu_1, mu_cpu_2, sigma_cpu_1, sigma_cpu_2 = bimode(sim_data)
    amps = np.linspace(-1, 1, 1000)
    cpu_probs = (dist(amps, mu_cpu_1, sigma_cpu_1) + dist(amps, mu_cpu_2, sigma_cpu_2))/2
    ax.plot(amps, cpu_probs, '--k', label='CPU')

    ax.legend(loc='lower right')

    ax.set_xlabel('Voltage')
    ax.set_ylabel('Probability Density')
    ax.set_title('DFE Output Histogram')
    plt.xlim([-.75, 1.25])

    fig.tight_layout()

    plot_name = os.path.join(args.fig_dir, 'rx_histograms')
    for fmt in fmts:
        plt.savefig(plot_name + '.' + fmt, bbox_inches='tight')

    plt.show()
    
if __name__=='__main__':
    main()
