import collections

class VerilogArray:
    def __init__(self, arr, mode='int'):
        self.arr = arr
        self.mode = mode

    def __str__(self):
        if self.mode.lower() in ['int']:
            def fmt(elem):
                return '{:d}'.format(elem)
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
    def __init__(self, name, value, type_=None):
        self.name = name
        self.value = value
        self.type_ = type_
        self.is_array = isinstance(self.value, collections.Iterable)

    @property
    def valstr(self):
        if self.is_array:
            return str(VerilogArray(arr=self.value, mode=self.type_))
        elif self.type_.lower() in ['int']:
            return '{:d}'.format(self.value)
        elif self.type_.lower() in ['float']:
            return '{:e}'.format(self.value)
        else:
            raise ValueError('Invalid formatting mode.')

    def __str__(self):
        arr = []
        arr.append('const')
        if self.type_ is not None:
            arr.append(self.type_)
        arr.append(self.name)
        if self.is_array:
            arr.append('[{}]'.format(len(self.value)))
        arr.append('=')
        arr.append(self.valstr)

        return ' '.join(arr)

class VerilogPackage:
    def __init__(self, name='globals'):
        self.name = name
        self.vars = []

    def add(self, var):
        self.vars.append(var)

    def __str__(self):
        retval = ''
        retval += 'package ' + self.name + ';\n'
        retval += '\n'
        for var in self.vars:
            retval += '    ' + str(var) + ';\n'
        retval += '\n'
        retval += 'endpackage //' + self.name + '\n'

        return retval

def main():
    arr = DefineVariable(name='MY_ARRAY', value=[1,2,3], type_='int')

    package = VerilogPackage()
    package.add(DefineVariable(name='TOTAL', value=456, type_='int'))
    package.add(arr)
    print(str(package))

if __name__=='__main__':
    main()
