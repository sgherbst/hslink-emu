# Makefile for running simulation

BUILD_DIR := ../build/
SHARED_DIR := ../shared/
CPU_DIR := ../cpu/

PACKAGES := $(BUILD_DIR)/time_package.sv $(BUILD_DIR)/signal_package.sv $(BUILD_DIR)/filter_package.sv
TOP := sys_test.sv
NCVERILOG := ncverilog
LIBS := -y $(SHARED_DIR) -y $(CPU_DIR)
INCS := 
TCL_CMD := -input hdl.tcl
OTHER_OPTS := +libext+.sv +nctimescale+1ns/1ps -sv +nc64bit -profile +ncaccess+rwc

.PHONY: sim clean

sim:
	$(NCVERILOG) $(PACKAGES) $(TOP) $(LIBS) $(INCS) $(OTHER_OPTS) $(TCL_CMD)

clean:
	@rm -rf INCA_libs waves.shm .simvision
	@rm -f ncverilog.history tx.txt rxp.txt rxn.txt ncsim.log ncverilog.log
