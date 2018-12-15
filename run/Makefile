# Steven Herbst (sherbst@stanford.edu)

# Makefile for building, simulating, and
# checking the mixed-signal emulator

#########################################
# simulation settings
# note that all TX and RX settings are
# built into the emulator, even when
# only one is exercised in simulation
#########################################

RX_SETTING = 4
TX_SETTING = 4
KP_LF = 256
KI_LF = 1
DCO_CODE_INIT = 6700
JITTER_SCALE_RX = 700
JITTER_SCALE_TX = 700

# 128 ns
TIME_TRIG = 18014398

# 2.048 us
# TIME_TRIG = 288230376

#########################################
# settings for testing specific features
#########################################

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

#########################################
# python options
# only python3 is supported at this time
#########################################
PYTHON = source ../env/bin/activate; python
PYTHON_OPTS += --build_dir $(BUILD_DIR)
PYTHON_OPTS += --channel_dir $(CHANNEL_DIR)
PYTHON_OPTS += --data_dir $(DATA_DIR)
PYTHON_OPTS += --rom_dir $(ROM_DIR)
PYTHON_OPTS += --fig_dir $(FIG_DIR)

#########################################
# git options
# used for cleaning up files
#########################################
GIT = git

#########################################
# simulation options
#########################################
SIM_CMD = xrun

# packages
SIM_PACK_LIST += time_package.sv
SIM_PACK_LIST += signal_package.sv
SIM_PACK_LIST += filter_package.sv
SIM_PACK_LIST += tx_package.sv
SIM_PACK_LIST += rx_package.sv
SIM_PACK_LIST += path_package.sv
SIM_PACK_LIST += lfsr_package.sv
SIM_PACKS = $(addprefix $(BUILD_DIR)/,$(SIM_PACK_LIST))

# libraries
SIM_LIB_LIST += $(SHARED_DIR)
SIM_LIB_LIST += $(CPU_DIR)
SIM_LIBS = $(addprefix -y ,$(SIM_LIB_LIST))

# defines
SIM_DEF_LIST += RX_SETTING=$(RX_SETTING)
SIM_DEF_LIST += TX_SETTING=$(TX_SETTING)
SIM_DEF_LIST += KP_LF=$(KP_LF)
SIM_DEF_LIST += KI_LF=$(KI_LF)
SIM_DEF_LIST += DCO_CODE_INIT=$(DCO_CODE_INIT)
SIM_DEF_LIST += TIME_TRIG=$(TIME_TRIG)
SIM_DEF_LIST += JITTER_SCALE_RX=$(JITTER_SCALE_RX)
SIM_DEF_LIST += JITTER_SCALE_TX=$(JITTER_SCALE_TX)
SIM_DEF_LIST += PWL_OVFL_CHK
SIM_DEFS = $(addprefix +define+,$(SIM_DEF_LIST))

# add other options
SIM_OPTS += $(SIM_PACKS)
SIM_OPTS += $(SIM_DEFS)
SIM_OPTS += $(SIM_LIBS)
SIM_OPTS += +libext+.sv
SIM_OPTS += -timescale 1ns/1ps
SIM_OPTS += -sv
SIM_OPTS += +xm64bit

# options for specific scenarios

# standard simulation (slowest but most visibility)
SIM_DEBUG_OPTS += -input sim.tcl
SIM_DEBUG_OPTS += -access +rwc

# lean simulation (faster with less visibility)
SIM_LEAN_OPTS += -input lean.tcl
SIM_LEAN_OPTS += -access +r

# profile simulation (fastest but no visibility)
SIM_PROFILE_OPTS += -input profile.tcl
SIM_PROFILE_OPTS += -profile

.PHONY: all build check check_ila check_filter sim sim_filter sim_profile clean

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
# full system sim commands
#########################

sim:
	$(SIM_CMD) $(SIM_OPTS) $(SIM_DEBUG_OPTS) sim.sv

sim_lean:
	$(SIM_CMD) $(SIM_OPTS) $(SIM_LEAN_OPTS) sim.sv

sim_profile:
	$(SIM_CMD) $(SIM_OPTS) $(SIM_PROFILE_OPTS) sim.sv

#########################
# subsystem sim commands
#########################

sim_filter:
	$(SIM_CMD) $(SIM_OPTS) $(SIM_DEBUG_OPTS) +define+FILTER_PWL_INDEX=$(FILTER_PWL_INDEX) sim_filter.sv

sim_dco:
	$(SIM_CMD) $(SIM_OPTS) $(SIM_DEBUG_OPTS) sim_dco.sv

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
