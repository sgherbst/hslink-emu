import collections

class VerilogArray:
    def __init__(self, arr, mode='int'):
        self.arr = arr
        self.mode = mode

    def __str__(self):
        if self.mode.lower() in ['int']:
            def fmt(elem):
                return '{:d}'.format(elem)
        elif self.mode.lower() in ['longint']:
            def fmt(elem):
                return '{:d}'.format(elem)
        elif self.mode.lower() in ['string']:
            def fmt(elem):
                return '"' + elem + '"'
        elif self.mode.lower() in ['float']:
            def fmt(elem):
                return '{:e}'.format(elem)
        else:
            raise ValueError('Invalid formatting mode.')

        retval = "'{"
        retval += ", ".join(fmt(elem) for elem in self.arr)
        retval += "}"

        return retval

class DefineVariable:
    def __init__(self, name, value, kind=None):
        self.name = name
        self.value = value
        self.kind = kind
        self.is_array = isinstance(self.value, collections.Iterable)

    @property
    def valstr(self):
        if self.is_array:
            return str(VerilogArray(arr=self.value, mode=self.kind))
        elif self.kind.lower() in ['int']:
            return '{:d}'.format(self.value)
        elif self.kind.lower() in ['longint']:
            return '{:d}'.format(self.value)
        elif self.kind.lower() in ['string']:
            return '"' + self.value + '"'
        elif self.kind.lower() in ['float']:
            return '{:e}'.format(self.value)
        else:
            raise ValueError('Invalid formatting mode.')

    def __str__(self):
        arr = []
        arr.append('const')
        if self.kind is not None:
            arr.append(self.kind)
        arr.append(self.name)
        if self.is_array:
            arr.append('[{}]'.format(len(self.value)))
        arr.append('=')
        arr.append(self.valstr)

        return ' '.join(arr)

class VerilogTypedef:
    def __init__(self, name, width, signed=False, kind='logic'):
        self.name = name
        self.width = width
        self.signed = signed
        self.kind = kind

    def __str__(self):
        arr = []
        arr.append('typdef')
        arr.append(self.kind)
        if self.signed:
            arr.append('signed')
        arr.append('[{}:{}]'.format(self.width-1, 0))
        arr.append(self.name)

        return ' '.join(arr)

class VerilogPackage:
    def __init__(self, name='globals'):
        self.name = name
        self.vars = []
        self.var_name_set = set()

    def add(self, var):
        assert var.name not in self.var_name_set, var.name
        self.var_name_set.add(var.name)

        self.vars.append(var)

    def __str__(self):
        retval = ''
        retval += 'package ' + self.name + ';\n'
        retval += '\n'
        for var in self.vars:
            retval += '    ' + str(var) + ';\n'
        retval += '\n'
        retval += 'endpackage // ' + self.name + '\n'

        return retval

    def write_to_file(self, fname):
        with open(fname, 'w') as f:
            f.write(str(self))

def main():
    arr = DefineVariable(name='MY_ARRAY', value=[1,2,3], kind='int')

    package = VerilogPackage()
    package.add(DefineVariable(name='TOTAL', value=456, kind='int'))
    package.add(arr)
    print(str(package))

if __name__=='__main__':
    main()
