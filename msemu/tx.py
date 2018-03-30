def ffe_coeffs(preset):
    # reference: https://www.ashtbit.net/applications/lfrunew/resource/PCIe_Equalization_v01.pdf
    result_dict ={
        0 : [0, .75, -.25],
        1: [0, .833, -.167],
        2: [0, .8, -.2],
        3: [0, .875, -.125],
        4: [0, 1, 0],
        5: [-.1, .9, 0],
        6: [-.125, .875, 0],
        7: [-.1, .7, -.2],
        8: [-.125, .75, -.125],
        9: [-.167, .833, 0],
        # preset 11 is for testing purposes
        11: [1]
    }
    return result_dict[preset]

def main():
    for k in range(10):
        print('Preset {}: {}'.format(k, ffe_coeffs(k)))

if __name__=='__main__':
    main()
