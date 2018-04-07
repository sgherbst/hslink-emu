# Makefile for running simulation

PYTHON := python3

BUILD_DIR := ../build/
SHARED_DIR := ../shared/
CPU_DIR := ../cpu/

PACKAGES := $(BUILD_DIR)/time_package.sv $(BUILD_DIR)/signal_package.sv $(BUILD_DIR)/filter_package.sv
NCVERILOG := ncverilog
LIBS := -y $(SHARED_DIR) -y $(CPU_DIR)
INCS := 
TCL_CMD := -input hdl.tcl
OTHER_OPTS := +libext+.sv +nctimescale+1ns/1ps -sv +nc64bit -profile +ncaccess+rwc

.PHONY: sim clean

sim:
	$(NCVERILOG) $(PACKAGES) sys_test.sv $(LIBS) $(INCS) $(OTHER_OPTS) $(TCL_CMD)

sim_filter_pwl:
	$(NCVERILOG) $(PACKAGES) filter_pwl_test.sv $(LIBS) $(INCS) $(OTHER_OPTS) $(TCL_CMD)

check:
	$(PYTHON) check.py

check_filter_pwl:
	$(PYTHON) check_filter_pwl.py

clean:
	@rm -rf INCA_libs waves.shm .simvision
	@rm -f ncverilog.history tx.txt rxp.txt rxn.txt ncsim.log ncverilog.log ncprof.out shm.prof
	@rm -f filter_pwl_emu.txt
