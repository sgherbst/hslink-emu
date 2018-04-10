# Makefile for running simulation

PYTHON := python3

RX_SETTING := 0
TX_SETTING := 10

# only for testing purposes...
FILTER_PWL_INDEX := 35

BUILD_DIR := ../build/
SHARED_DIR := ../shared/
CPU_DIR := ../cpu/

PACKAGES := $(BUILD_DIR)/time_package.sv $(BUILD_DIR)/signal_package.sv $(BUILD_DIR)/filter_package.sv $(BUILD_DIR)/tx_package.sv $(CPU_DIR)/globals.sv
NCVERILOG := ncverilog
LIBS := -y $(SHARED_DIR) -y $(CPU_DIR)
INCS := 
TCL_CMD := -input hdl.tcl
OTHER_OPTS := +libext+.sv +nctimescale+1ns/1ps -sv +nc64bit +ncaccess+rwc +define+RX_SETTING=$(RX_SETTING) +define+TX_SETTING=$(TX_SETTING)

.PHONY: sim clean

sim:
	$(NCVERILOG) $(PACKAGES) sys_test.sv $(LIBS) $(INCS) $(OTHER_OPTS) -input hdl.tcl

profile:
	$(NCVERILOG) $(PACKAGES) sys_test.sv $(LIBS) $(INCS) $(OTHER_OPTS) -input profile.tcl +define+PROFILE -profile

sim_filter_pwl:
	$(NCVERILOG) $(PACKAGES) filter_pwl_test.sv $(LIBS) $(INCS) $(OTHER_OPTS) $(TCL_CMD) +define+FILTER_PWL_INDEX=$(FILTER_PWL_INDEX)

check:
	$(PYTHON) check.py --rx_setting $(RX_SETTING)

check_filter_pwl:
	$(PYTHON) check_filter_pwl.py --rx_setting $(RX_SETTING)

clean:
	@rm -rf INCA_libs waves.shm .simvision
	@rm -f ncverilog.history tx.txt rxp.txt rxn.txt ncsim.log ncverilog.log ncprof.out shm.prof
	@rm -f filter_pwl_emu.txt ncverilog.key
