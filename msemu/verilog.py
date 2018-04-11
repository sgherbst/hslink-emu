import collections
import os.path

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
    def __init__(self, name='globals', time_unit='1ns', time_res='1ps', use_timescale=True):
        self.name = name
        self.vars = []
        self.var_names = set()
        self.time_unit = time_unit
        self.time_res = time_res
        self.use_timescale = use_timescale

    def add(self, var):
        # note: a dictionary is not used here to ensure a well-defined output order
        # this is helpful when comparing the output of various versions of the 
        # build program

        # make sure that we haven't already added a variable with this name
        assert var.name not in self.var_names
        self.var_names.add(var.name)

        # add the variable
        self.vars.append(var)

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
        for var in self.vars:
            retval += '    ' + str(var) + ';\n'
        retval += '\n'
        retval += 'endpackage // ' + self.name + '\n'

        return retval

    def write(self, dir_name):
        file_name = os.path.join(dir_name, self.name + '.sv')
        with open(file_name, 'w') as f:
            f.write(str(self))

def main():
    arr = VerilogConstant(name='MY_ARRAY', value=[1,2,3], kind='int')

    package = VerilogPackage()
    package.add(VerilogConstant(name='TOTAL', value=456, kind='int'))
    package.add(arr)
    package.add(VerilogConstant(name='SINGLE_STRING', value='abc123', kind='string'))
    package.add(VerilogConstant(name='STRING_ARRAY', value=['foo', 'bar', '12345678'], kind='string'))
    print(str(package))

if __name__=='__main__':
    main()
