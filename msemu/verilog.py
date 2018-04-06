import collections

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
    def format_array(vals, kind):
        retval = "'{"
        retval += ", ".join(VerilogFormatting.format_single_value(val=val, kind=kind) for val in vals)
        retval += "}"

        return retval

    @staticmethod
    def format(val_or_vals, kind):
        if isinstance(val_or_vals, collections.Iterable):
            return VerilogFormatting.format_array(vals=val_or_vals, kind=kind)
        else:
            return VerilogFormatting.format_single_value(val=val_or_vals, kind=kind)

class VerilogConstant:
    def __init__(self, name, value, kind=None):
        self.name = name
        self.value = value
        self.kind = kind

    def __str__(self):
        arr = []

        arr.append('parameter')
        if self.kind is not None:
            arr.append(self.kind)
        arr.append(self.name)
        if isinstance(self.value, collections.Iterable):
            arr.append('[{}]'.format(len(self.value)))
        arr.append('=')
        arr.append(VerilogFormatting.format(self.value, kind=self.kind))

        return ' '.join(arr)

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

class VerilogPackage:
    def __init__(self, name='globals'):
        self.name = name
        self.vars = {}

    def add(self, var):
        # make sure that
        assert var.name not in self.vars
        self.vars[var.name] = var

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
        retval += 'package ' + self.name + ';\n'
        retval += '\n'
        for var in self.vars.values():
            retval += '    ' + str(var) + ';\n'
        retval += '\n'
        retval += 'endpackage // ' + self.name + '\n'

        return retval

    def write_to_file(self, fname=None):
        if fname is None:
            fname = self.name + '.sv'
        with open(fname, 'w') as f:
            f.write(str(self))

def main():
    arr = VerilogConstant(name='MY_ARRAY', value=[1,2,3], kind='int')

    package = VerilogPackage()
    package.add(VerilogConstant(name='TOTAL', value=456, kind='int'))
    package.add(arr)
    print(str(package))

if __name__=='__main__':
    main()
