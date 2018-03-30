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

def main():
    print(str(VerilogArray([1,2,3], mode='int')))

if __name__=='__main__':
    main()
