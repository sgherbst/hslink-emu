import collections
import os.path
import re

class VerilogFormatting:
    @staticmethod
    def format_single_value(val, kind):
        if kind.lower() in ['int']:
            return '{:d}'.format(val)
        elif kind.lower() in ['longint']:
            return '{:d}'.format(val)
        elif kind.lower() in ['string']:
            return '"{}"'.format(val)
        elif kind.lower() in ['float']:
            return '{:e}'.format(val)
        else:
            raise ValueError('Invalid formatting mode.')

    @staticmethod
    def format(val_or_vals, kind):
        if isinstance(val_or_vals, (int, float, str)):
            return VerilogFormatting.format_single_value(val=val_or_vals, kind=kind)
        elif isinstance(val_or_vals, collections.Iterable):
            retval = "'{"
            retval += ", ".join(VerilogFormatting.format(val, kind=kind) for val in val_or_vals)
            retval += "}"
            return retval
        else:
            raise ValueError('Unsupported type.')

    @staticmethod
    def get_array_dims(val_or_vals):
        if isinstance(val_or_vals, (int, float, str)):
            return ''
        elif isinstance(val_or_vals, collections.Iterable):
            subdims = [VerilogFormatting.get_array_dims(val) for val in val_or_vals]
            assert all(subdim==subdims[0] for subdim in subdims)
            return '[{}]'.format(len(subdims)) + subdims[0]
        else:
            raise ValueError('Unsupported type.')

    @staticmethod
    def get_str_size(val_or_vals, char_size=8, include_null=True):
        if isinstance(val_or_vals, str):
            str_len = len(val_or_vals)
            if include_null:
                str_len += 1
            return str_len*char_size
        elif isinstance(val_or_vals, collections.Iterable):
            return max(VerilogFormatting.get_str_size(val, char_size=char_size) for val in val_or_vals)
        else:
            raise ValueError('Unsupported type.')

    @staticmethod
    def from_str(inpt, kind):
        inpt = inpt.strip()

        if inpt.startswith("'{"):
            assert inpt.endswith("}")
            inpt = inpt[2:-1]
            return [VerilogFormatting.from_str(elem, kind) for elem in inpt.split(',')]
        elif kind == 'int':
            return int(inpt.strip())
        elif kind == 'longint':
            return int(inpt.strip())
        elif kind == 'string':
            assert inpt.startswith('"')
            assert inpt.endswith('"')
            return inpt[1:-1]
        else:
            raise ValueError('Unsupported type.')

class VerilogConstant:
    def __init__(self, name, value, kind=None):
        self.name = name
        self.value = value
        self.kind = kind

    def __str__(self):
        arr = []

        arr.append('parameter')
        if self.kind is None:
            pass
        elif self.kind.lower() not in ['string']:
            arr.append(self.kind)
        elif isinstance(self.value, str):
            pass
        elif isinstance(self.value, collections.Iterable):
            max_str_size = VerilogFormatting.get_str_size(self.value)
            arr.append('[{}:{}]'.format(max_str_size-1, 0))
        else:
            raise ValueError("Seems that 'kind' doesn't match 'value'.")

        arr.append(self.name)

        # add array dimensions if appropriate
        if isinstance(self.value, (int, float, str)):
            pass
        elif isinstance(self.value, collections.Iterable):
            arr.append(VerilogFormatting.get_array_dims(self.value))
        else:
            raise ValueError('Unsupported type.')

        arr.append('=')
        arr.append(VerilogFormatting.format(self.value, kind=self.kind))

        return ' '.join(arr)

    @staticmethod
    def from_str(inpt):
        slice_pat = r'\[\s*\d+\s*:\s*\d+\s*\]'

        pat = r'parameter\s+'
        pat += r'(int\s+|longint\s+|{}\s+)?'.format(slice_pat)
        pat += r'([a-zA-Z0-9_]+)\s*'
        pat += '(\s*\[\s*\d+\s*\]\s*)*\s*'
        pat += r'='
        pat += r'(.+)'
        pat += r';'

        match = re.match(pat, inpt)
        groups = match.groups()

        kind = groups[0]
        if kind is None:
            kind = 'string'
        elif re.match(slice_pat, kind.strip()):
            kind = 'string'
        else:
            kind = kind.strip()

        name = groups[1]

        value = VerilogFormatting.from_str(groups[3], kind=kind)

        return VerilogConstant(name=name, value=value, kind=kind)

class VerilogTypedef:
    def __init__(self, name, width, signed=False, kind='logic'):
        self.name = name
        self.width = width
        self.signed = signed
        self.kind = kind

    def __str__(self):
        arr = []

        arr.append('typedef')
        arr.append(self.kind)
        if self.signed:
            arr.append('signed')
        arr.append('[{}:{}]'.format(self.width-1, 0))
        arr.append(self.name)

        return ' '.join(arr)

    @staticmethod
    def from_str(inpt):
        slice_pat = r'\[\s*(\d+)\s*:\s*(\d+)\s*\]'

        pat = r'typedef\s+'
        pat += r'(logic\s+)' # only logic type supported for now
        pat += r'(signed\s+)?'
        pat += r'{}\s+'.format(slice_pat)
        pat += r'([a-zA-Z0-9_]+)\s*;'

        match = re.match(pat, inpt)
        groups = match.groups()

        kind = groups[0].strip()

        if groups[1] is None:
            signed = False
        else:
            signed = True

        msb = int(groups[2])
        lsb = int(groups[3])
        width = msb - lsb + 1

        name = groups[4]

        return VerilogTypedef(name=name, width=width, signed=signed, kind=kind)

class VerilogPackage:
    def __init__(self, name='globals', time_unit='1ns', time_res='1ps', use_timescale=True):
        self.name = name
        self.time_unit = time_unit
        self.time_res = time_res
        self.use_timescale = use_timescale

        # used to keep track of all variables
        self.names = []
        self._vars = {}

    def add(self, var):
        # make sure that we haven't already added a variable with this name
        assert var.name not in self._vars

        # add variable to the dictionary
        self._vars[var.name] = var

        # add the variable to the var_name list to ensure that the definition order
        # is preserved.  this is useful when diff-ing files in the build directory
        self.names.append(var.name)

    def get(self, name):
        return self._vars[name]

    def add_fixed_format(self, format, prefix):
        self.add(VerilogConstant(name = prefix.upper()+'_WIDTH',
                                 value = format.n,
                                 kind = 'int'))

        self.add(VerilogConstant(name = prefix.upper()+'_POINT',
                                 value = format.point,
                                 kind = 'int'))

        self.add(VerilogTypedef(name = prefix.upper()+'_FORMAT',
                                width = format.n,
                                signed = format.signed))

    def __str__(self):
        retval = ''

        if self.use_timescale:
            retval += '`timescale {}/{}\n'.format(self.time_unit, self.time_res)
            retval += '\n'
            
        retval += 'package ' + self.name + ';\n'
        retval += '\n'
        for name in self.names:
            var = self.get(name)
            retval += '    ' + str(var) + ';\n'
        retval += '\n'
        retval += 'endpackage // ' + self.name + '\n'

        return retval

    def write(self, dir_name):
        file_name = os.path.join(dir_name, self.name + '.sv')
        with open(file_name, 'w') as f:
            f.write(str(self))

    @staticmethod
    def from_str(inpt):
        lines = [line.strip() for line in inpt.splitlines()]

        # TODO first pass: get information needed to instantiate package
        name = None
        time_unit = None
        time_res = None
        use_timescale = False
        for line in lines:
            if line.startswith('package'):
                pat = r'package\s+([a-zA-Z_0-9]+)\s*;'
                match = re.match(pat, line)
                name = match.groups()[0]
            elif line.startswith('`timescale'):
                pat = r'`timescale\s+([a-zA-Z_0-9]+)\s*/\s*([a-zA-Z_0-9]+)'
                match = re.match(pat, line)
                time_unit = match.groups()[0]
                time_res = match.groups()[1]
                use_timescale = True

        pack = VerilogPackage(name=name, time_unit=time_unit, time_res=time_res, use_timescale=use_timescale)

        # second pass: read parameters and typedefs
        for line in lines:
            if line.startswith('parameter'):
                pack.add(VerilogConstant.from_str(line))
            elif line.startswith('typedef'):
                pack.add(VerilogTypedef.from_str(line))

        return pack

    @staticmethod
    def from_file(file_name):
        with open(file_name, 'r') as f:
            inpt = f.read()
        return VerilogPackage.from_str(inpt)

def main():
    arr = VerilogConstant(name='MY_ARRAY', value=[1,2,3], kind='int')

    package = VerilogPackage()
    package.add(VerilogConstant(name='TOTAL', value=456, kind='int'))
    package.add(arr)
    package.add(VerilogConstant(name='SINGLE_STRING', value='abc123', kind='string'))
    package.add(VerilogConstant(name='STRING_ARRAY', value=['foo', 'bar', '12345678'], kind='string'))
    package.add(VerilogTypedef(name='SAMPLE_SIGNED_FORMAT', width=22, signed=True))
    package.add(VerilogTypedef(name='SAMPLE_UNSIGNED_FORMAT', width=42, signed=False))
    package_str = str(package)

    print(package_str)
    print()

    package_str_2 = str(VerilogPackage.from_str(package_str))
    print(package_str_2)
    print()

    assert package_str == package_str_2, 'Strings do not match :-('
    print('Both strings match :-)')

if __name__=='__main__':
    main()
