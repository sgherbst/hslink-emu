# Event-driven FPGA emulation model of a high-speed link

## Introduction

This example illustrates an event-driven methodology for precisely modeling analog dynamics on FPGAs, capable of achieving  ~1000x speedup as compared to optimized CPU simulations.  If you're interested to learn more about the approach, please consider reading our ICCAD 2018 paper, "Fast FPGA emulation of analog dynamics in digitally-driven systems" ([https://doi.org/10.1145/3240765.3240808](https://doi.org/10.1145/3240765.3240808)).

## Prerequisites

1. Computer running Linux (tested with Ubuntu 18.04).
2. Vivado installation (tested with Vivado 2018.3 Design Edition).  The PATH variable should be set to include the **vivado** command.
3. Python3 installation (tested with Python 3.7 installed through miniconda).
4. [ZC706 FPGA Board](https://www.xilinx.com/products/boards-and-kits/ek-z7-zc706-g.html).

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
3. Build the models associate with the project.  This should take 3-4 minutes, most of which is spent constructing lookup tables used to model the analog dynamics.
```shell
> cd run
> make build
```
4. Generate the FPGA bitstream.  This should take about 15-20 minutes.
```shell
> cd run
> make fpga
```
5. Plug in the ZC706 board: connect its power cable and connect a micro-USB cable between the board and your computer.  The flip the power switch to the "ON" position.  The board fan should turn on at this point.
6. In a separate tab/window, launch a server for handling Vivado TCL commands.  This reduces the overhead in running the subsequent steps as compared to individual Vivado invocations in batch mode.  (You can exit the server by pressing Ctrl-C.)
```shell
> python ../msemu/server.py
```
7. Wait for the server to say that it's ready to accept commands, then go back to the original tab/window and program the FPGA.  This should take 10-20, after which point the emulator is programmed and ready to use.
```shell
> make program
```
8. As a first example, use the emulator the simulate the startup dynamics of the high-speed link.  This command will present you with a interactive graph of the digitally-controlled oscillator (DCO) code over time.
```shell
> make emu_dco
```
9. As a second example, run a loopback test to make sure the link can receive bits without errors.  This command will send about 40 million bits through the link, and should take about 4 seconds, demonstrating a 10 Mb/s emulation throughput.  This is about 1000x faster than the fastest reported CPU simulations of such a system.
```shell
> make emu_loopback
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

### Using a different FPGA board
1. In fpga/constr.xdc, update the "System Clock" and "Status Outputs" sections.  The 

## Citing

If you found this work helpful, please consider citing the ICCAD 2018 paper associated with the work!

Steven Herbst, Byong Chan Lim, and Mark Horowitz. 2018. Fast FPGA emulation of analog dynamics in digitally-driven systems. In Proceedings of the International Conference on Computer-Aided Design (ICCAD '18). ACM, New York, NY, USA, Article 131, 8 pages. DOI: [https://doi.org/10.1145/3240765.3240808](https://doi.org/10.1145/3240765.3240808)
