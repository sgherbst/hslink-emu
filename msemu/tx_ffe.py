class TxFFE:
    def __init__(self):
        # reference: https://www.ashtbit.net/applications/lfrunew/resource/PCIe_Equalization_v01.pdf
        self._taps_array = [
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

    @property
    def taps_array(self):
        return self._taps_array

    @property
    def settings(self):
        retval = []

        for taps in self.taps_array:
            setting = []
            for tap in taps:
                setting.append([-tap, +tap])
            retval.append(setting)

        return retval

    @property
    def n_settings(self):
        return len(self.taps_array)

    @property
    def n_taps(self):
        # get length of taps
        n0 = len(self.taps_array[0])
        n_taps_array = [len(taps) for taps in self.taps_array[1:]]

        # make sure they are all equal
        assert all(n==n0 for n in n_taps_array)

        # return length
        return n0