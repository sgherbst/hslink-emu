# Steven Herbst (sherbst@stanford.edu)

# Makefile for building, simulating, and
# checking the mixed-signal emulator

#########################################
# simulation configuration
#########################################

# TIME_TRIG values:
# 128 ns        ->  18014398
# 2.048 us      ->  288230376
TIME_TRIG = 18014398

RX_SETTING = 4

FILTER_PWL_INDEX = 35

#########################################
# directory structure
#########################################

TOP_DIR = $(abspath ../)

BUILD_DIR = $(abspath $(TOP_DIR)/build/)
CHANNEL_DIR = $(abspath $(TOP_DIR)/channel/)
CPU_DIR = $(abspath $(TOP_DIR)/cpu/)
DATA_DIR = $(abspath $(TOP_DIR)/data/)
FPGA_DIR = $(abspath $(TOP_DIR)/fpga/)
SHARED_DIR = $(abspath $(TOP_DIR)/shared/)
FIG_DIR = $(abspath $(TOP_DIR)/figs/)

ROM_DIR = $(abspath $(BUILD_DIR)/roms/)
SIM_DIR = $(abspath $(BUILD_DIR)/project/project.sim/sim_1/behav/xsim/)

#########################################
# python options
#########################################

PYTHON = python
PYTHON_OPTS += --build_dir $(BUILD_DIR)
PYTHON_OPTS += --channel_dir $(CHANNEL_DIR)
PYTHON_OPTS += --data_dir $(DATA_DIR)
PYTHON_OPTS += --rom_dir $(ROM_DIR)
PYTHON_OPTS += --fig_dir $(FIG_DIR)
PYTHON_OPTS += --sim_dir $(SIM_DIR)

#########################################
# git options
# used for cleaning up files
#########################################

GIT = git

#########################################
# simulation options
#########################################

SIM_CMD = rm -rf ../build/project && vivado -nolog -nojournal -notrace -mode batch

all: build sim check

#########################
# python commands
#########################

build:
	$(PYTHON) build.py $(PYTHON_OPTS)

check:
	$(PYTHON) check.py $(PYTHON_OPTS) --rx_setting $(RX_SETTING)

check_filter:
	$(PYTHON) check_filter.py $(PYTHON_OPTS) --rx_setting $(RX_SETTING)

check_dco:
	$(PYTHON) check_dco.py $(PYTHON_OPTS) 

#########################
# simulation commands
#########################

sim:
	$(SIM_CMD) -source sim.tcl -tclargs $(RX_SETTING) $(TIME_TRIG)

sim_filter:
	$(SIM_CMD) -source sim_filter.tcl -tclargs $(RX_SETTING) $(FILTER_PWL_INDEX)

sim_dco:
	$(SIM_CMD) -source sim_dco.tcl

view:
	gtkwave $(SIM_DIR)/dump.vcd &

#########################
# figure generation commands
#########################

all_figs: plot_input_hist plot_dco_settling check_ila plot_pies plot_steps plot_rom_bits

check_ila:
	$(PYTHON) check.py $(PYTHON_OPTS) --rx_setting $(RX_SETTING) --use_ila

plot_dco_settling:
	$(PYTHON) plot_dco_settling.py $(PYTHON_OPTS)

plot_input_hist:
	$(PYTHON) plot_input_hist.py $(PYTHON_OPTS)

plot_pies:
	$(PYTHON) plot_pies.py $(PYTHON_OPTS)

plot_rom_bits:
	$(PYTHON) plot_rom_bits.py $(PYTHON_OPTS)

plot_pwl:
	$(PYTHON) plot_pwl.py $(PYTHON_OPTS)

plot_pulses:
	$(PYTHON) plot_pulses.py $(PYTHON_OPTS)

#########################
# figure generation commands
#########################

measure_all: ila_sweep_write ila_sweep_read check_ila_loopback check_ila_jitter

ila_sweep_write:
	$(PYTHON) process_ila_sweep.py $(PYTHON_OPTS) --write

ila_sweep_read:
	$(PYTHON) process_ila_sweep.py $(PYTHON_OPTS) --read

check_ila_loopback:
	$(PYTHON) check_ila_loopback.py $(PYTHON_OPTS) 

check_ila_jitter:
	$(PYTHON) check_ila_jitter.py $(PYTHON_OPTS) 

plot_steps:
	$(PYTHON) plot_steps.py $(PYTHON_OPTS) 

analyze_roms:
	$(PYTHON) analyze_roms.py $(PYTHON_OPTS) 

sim_python:
	$(PYTHON) sim_python.py $(PYTHON_OPTS) 

#########################
# cleaning commands
#########################

clean:
	$(GIT) clean -xdf -e build/ -e data/ -e channel/
