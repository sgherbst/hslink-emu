import matplotlib.pyplot as plt
import re
import collections

class Utilization:
    def __init__(self, init_props=None):
        self.props = { 'Slice LUTs': 0,
                       'Slice Registers': 0,
                       'DSPs': 0,
                       'Block RAM Tile': 0 }
        if init_props is not None:
            self.add(init_props)

    def add(self, props):
        for prop in self.props:
            assert props[prop] >= 0
            self.props[prop] += props[prop]

    def sub(self, props):
        for prop in self.props:
            assert props[prop] >= 0
            self.props[prop] -= props[prop]
            assert self.props[prop] >= 0, print(self.props[prop], prop)

    def clone(self):
        util = Utilization()
        util.props = self.props.copy()
        return util

    @property
    def lut(self):
        return self.props['Slice LUTs']

    @property
    def ff(self):
        return self.props['Slice Registers']

    @property
    def dsp(self):
        return self.props['DSPs']

    @property
    def bram(self):
        return self.props['Block RAM Tile']

class ResourceCSV:
    def __init__(self, file_name):
        self.rows = {}

        with open(file_name, 'r') as f:
            lines = f.readlines()
            self.headers = lines[0].strip().split(',')

            for line in lines[1:]:
                cols =  line.split(',')

                name = cols[0]
                self.rows[name] = {}

                for k, col in enumerate(cols[1:]):
                    self.rows[name][self.headers[k+1]] = float(col)

    def get_matches(self, pat):
        comp = re.compile(pat)

        result = []
        for key, value in self.rows.items():
            match = comp.match(key)
            if match is not None:
                result.append((match, value))

        return result

    def get_util(self, pat):
        matches = self.get_matches(pat)
        assert len(matches) == 1

        util = Utilization()
        util.add(matches[0][1])

        return util

    def get_utils(self, pat):
        util = Utilization()
        matches = self.get_matches(pat)

        for _, row in matches:
            util.add(row)

        return util

class ResourceAllocation:
    def __init__(self, top, other_name='Other'):
        self.top = top

        self.cats = {other_name: self.top.clone()}
        self.other = self.cats[other_name]

    def add(self, util_or_utils, cat_name):
        if cat_name not in self.cats:
            self.cats[cat_name] = Utilization()

        if not isinstance(util_or_utils, collections.Iterable):
            utils = [util_or_utils]
        else:
            utils = util_or_utils

        for util in utils:
            self.cats[cat_name].add(util.props)
            self.other.sub(util.props)

    def plot(self):
        f, axarr = plt.subplots(2, 2)

        keys = [key for key in self.cats.keys() if self.cats[key].bram > 0]
        ResourceAllocation.plot_single(axarr[0, 0], 'BRAM', [self.cats[key].bram for key in keys], keys)

        keys = [key for key in self.cats.keys() if self.cats[key].dsp > 0]
        ResourceAllocation.plot_single(axarr[0, 1], 'DSP', [self.cats[key].dsp for key in keys], keys)

        keys = [key for key in self.cats.keys() if self.cats[key].lut > 0]
        ResourceAllocation.plot_single(axarr[1, 0], 'LUT', [self.cats[key].lut for key in keys], keys)

        keys = [key for key in self.cats.keys() if self.cats[key].ff > 0]
        ResourceAllocation.plot_single(axarr[1, 1], 'FF', [self.cats[key].ff for key in keys], keys)

    @staticmethod
    def plot_single(ax, title, sizes, labels):
        ax.pie(sizes, labels=labels, autopct='%1.1f%%')
        ax.set_title(title)
        ax.axis('equal')