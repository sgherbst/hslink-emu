from time import sleep
from msemu.server import get_client
from tqdm import tqdm
from argparse import ArgumentParser

def main(bit_rate=8e9, time_exponent=-47):
    # read in command-line arguments
    parser = ArgumentParser()
    parser.add_argument('--start_time', type=float, default=10e-6)
    parser.add_argument('--stop_time', type=float, default=5e-3)
    parser.add_argument('--dco_init', type=int, default=1000)
    parser.add_argument('--ki_lf', type=int, default=8)
    parser.add_argument('--kp_lf', type=int, default=256)
    args = parser.parse_args()

    # get the client
    s = get_client()

    # configure the start/stop times

    start_time_int = int(round(args.start_time*(2**-time_exponent)))
    stop_time_int = int(round(args.stop_time*(2**-time_exponent)))

    s.set_vio('start_time', str(start_time_int))
    s.set_vio('stop_time', str(stop_time_int))
    s.set_vio('dco_init', str(args.dco_init))
    s.set_vio('ki_lf', str(args.ki_lf))
    s.set_vio('kp_lf', str(args.kp_lf))

    # pulse reset

    s.pulse_reset()

    # main loop

    def get_int(name):
        return int(s.get_vio(name))

    total_bits = int(round((args.stop_time-args.start_time)*bit_rate))

    s.refresh_hw_vio('vio_0_i')

    with tqdm(total=total_bits) as pbar:
        while (get_int('rx_total_bits') < 0.999*total_bits):
            pbar.update(get_int('rx_total_bits') - pbar.n)
            sleep(0.1)
            s.refresh_hw_vio('vio_0_i')

    s.refresh_hw_vio('vio_0_i')

    print('Tested {:0.1f} Mb'.format(1e-6*get_int('rx_total_bits')))
    print('Number incorrect bits: {:0d}'.format(get_int('rx_bad_bits')))
    print('Bit error rate: {:0.1e}'.format(get_int('rx_bad_bits')/get_int('rx_total_bits')))

if __name__ == '__main__':
    main()