from math import log2, ceil
class TxFFE:
    def __init__(self):
        # reference: https://www.ashtbit.net/applications/lfrunew/resource/PCIe_Equalization_v01.pdf
        self._tap_table = [
            [0, .75, -.25],             # 0
            [0, .833, -.167],           # 1
            [0, .8, -.2],               # 2
            [0, .875, -.125],           # 3
            [0, 1, 0],                  # 4
            [-.1, .9, 0],               # 5
            [-.125, .875, 0],           # 6
            [-.1, .7, -.2],             # 7
            [-.125, .75, -.125],        # 8
            [-.167, .833, 0],           # 9
            [1, 0, 0]                   # 10 (testing purposes)
        ]

        # build the array of different settings
        self.create_setting_array()

    @property
    def n_settings(self):
        return len(self._tap_table)

    @property
    def n_taps(self):
        # get length of taps
        n_first = len(self.tap_table[0])
        n_rest = [len(taps) for taps in self.tap_table[1:]]

        # make sure they are all equal
        assert all(n == n_first for n in n_rest)

        # return length
        return n_first

    @property
    def tap_table(self):
        return self._tap_table

    @property
    def settings(self):
        return self._settings

    @property
    def setting_bits(self):
        return int(ceil(log2(self.n_settings)))

    @property
    def setting_padding(self):
        return ((1 << self.setting_bits) - self.n_settings)

    def create_setting_array(self):
        self._settings = []
        for taps in self.tap_table:
            self._settings.append([])
            for hist in range(1<<self.n_taps):
                self._settings[-1].append(0)
                for k in range(self.n_taps):
                    if ((hist >> k) & 1) == 1:
                        self._settings[-1][-1] += taps[k]
                    else:
                        self._settings[-1][-1] -= taps[k]

    def write_table(self, file_name, fixed_format):
        with open(file_name, 'w') as f:
            # write the bias values into a table
            for setting in self.settings:
                setting_strs = fixed_format.bin_str(setting)
                for setting_str in setting_strs:
                    f.write(setting_str + '\n')

            # pad the end with zeros as necessary
            zero_str = '0'*(fixed_format.n)
            for i in range(self.setting_padding):
                for j in range(1<< self.n_taps):
                    f.write(zero_str+'\n')

def main():
    tx_ffe = TxFFE()
    print(tx_ffe.settings)

if __name__ == '__main__':
    main()