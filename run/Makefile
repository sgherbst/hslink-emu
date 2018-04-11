# Steven Herbst (sherbst@stanford.edu)

# Makefile for building, simulating, and
# checking the mixed-signal emulator

#########################################
# simulation settings
# note that all TX and RX settings are
# built into the emulator, even when
# only one is exercised in simulation
#########################################

RX_SETTING = 0
TX_SETTING = 10

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

ROM_DIR = $(abspath $(BUILD_DIR)/roms/)

#########################################
# python options
# only python3 is supported at this time
#########################################
PYTHON = python3
PYTHON_OPTS += --build_dir $(BUILD_DIR)
PYTHON_OPTS += --channel_dir $(CHANNEL_DIR)
PYTHON_OPTS += --data_dir $(DATA_DIR)
PYTHON_OPTS += --rom_dir $(ROM_DIR)

#########################################
# git options
# used for cleaning up files
#########################################
GIT = git

#########################################
# simulation options
#########################################
SIM_CMD = irun

# packages
SIM_PACK_LIST += time_package.sv
SIM_PACK_LIST += signal_package.sv
SIM_PACK_LIST += filter_package.sv
SIM_PACK_LIST += tx_package.sv
SIM_PACK_LIST += path_package.sv
SIM_PACKS = $(addprefix $(BUILD_DIR)/,$(SIM_PACK_LIST))

# libraries
SIM_LIB_LIST += $(SHARED_DIR)
SIM_LIB_LIST += $(CPU_DIR)
SIM_LIBS = $(addprefix -y ,$(SIM_LIB_LIST))

# defines
SIM_DEF_LIST += RX_SETTING=$(RX_SETTING)
SIM_DEF_LIST += TX_SETTING=$(TX_SETTING)
SIM_DEFS = $(addprefix +define+,$(SIM_DEF_LIST))

# add other options
SIM_OPTS += $(SIM_PACKS)
SIM_OPTS += $(SIM_DEFS)
SIM_OPTS += $(SIM_LIBS)
SIM_OPTS += +libext+.sv
SIM_OPTS += -timescale 1ns/1ps
SIM_OPTS += -sv
SIM_OPTS += +nc64bit 

# options for specific scenarios

# standard simulation (slow but more visibility)
SIM_DEBUG_OPTS += -input sim.tcl
SIM_DEBUG_OPTS += -access +rwc
SIM_DEBUG_OPTS += +define+USE_ADC=1

# profile simulation (fast but no visibility)
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

check_ila:
	$(PYTHON) check.py $(PYTHON_OPTS) --rx_setting $(RX_SETTING) --use_ila

check_filter:
	$(PYTHON) check_filter.py $(PYTHON_OPTS) --rx_setting $(RX_SETTING)

#########################
# sim commands
#########################

sim:
	$(SIM_CMD) $(SIM_OPTS) $(SIM_DEBUG_OPTS) sim.sv

sim_filter:
	$(SIM_CMD) $(SIM_OPTS) $(SIM_DEBUG_OPTS) +define+PULSE_INDEX=$(PULSE_INDEX) sim_filter.sv

sim_profile:
	$(SIM_CMD) $(SIM_OPTS) $(SIM_PROFILE_OPTS) sim.sv

#########################
# cleaning commands
#########################

clean:
	$(GIT) clean -xdf -e build/ -e data/ -e channel/
