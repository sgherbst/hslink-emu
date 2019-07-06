# Event-driven FPGA emulation model of a high-speed link

## Introduction



## Installation

The instructions below assume that **python** and **pip** commands refer to a Python3 installation.

1. Clone the repository and go into the top-level folder.
```shell
> git clone https://github.com/sgherbst/hslink-emu.git
> cd hslink-emu
```
2. Install the Python package associated with this project:
```shell
> pip install -e .
```
3. Build the models associate with the project.
```shell
> cd run
> make build
```

## Customization

### Changing the CTLE transfer function
1. Go to hslink-emu/msemu/ctle.py, then add your own values for the coefficients of the numerator ("num") and denominator ("den") polynomials.  This should be around line 139.
2. Comment out lines 125-135 because they are specific to the PCIe reference CTLE design

### Changing the channel response
1. Create a directory called "channel" in the top-level hslink-emu directory.
2. Put your own S-parameter file in the channel directory.  The file should be Touchstone S4P (four port) and the port assignment numbers must match figure 3 of https://www.aesa-cortaillod.com/fileadmin/documents/knowledge/AN_150421_E_Single_ended_S_Parameters.pdf.
3. Go to hslink-emu/msemu/rf.py, then change **file_name** value to the name of your S-parameter file.

### If you only have one "CTLE" mode
1. To avoid building 16 different models, of hslink-emu/msemu/ctle.py.
2. On line 85, change to "db_vals = list(range(2))". 
