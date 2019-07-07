import argparse
import pathlib

def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('--build_dir', type=str, help='Directory where packages should be placed.')
    parser.add_argument('--rom_dir', type=str, help='Directory where ROM files should be placed.')
    parser.add_argument('--data_dir', type=str, help='Directory where data should be placed.')
    parser.add_argument('--channel_dir', type=str, help='Directory where channel measurements should be placed.')
    parser.add_argument('--fig_dir', type=str, help='Directory where channel measurements should be placed.')
    parser.add_argument('--sim_dir', type=str, help='Directory where simulation outputs are stored.')

    return parser

def mkdir_p(dir_name):
    pathlib.Path(dir_name).mkdir(parents=True, exist_ok=True)
