# Makefile for running simulation

sim:
	ncverilog ../build/filter_package.sv ../build/time_package.sv ../build/signal_package.sv sys_test.sv -y ../shared -y ../cpu -y ../build -y ../build/roms -incdir ../shared -incdir ../cpu -incdir ../build -incdir ../build/roms +libext+.sv +nctimescale+1ns/1ps -sv +nc64bit -input hdl.tcl -profile +ncaccess+rwc

clean:
	@rm -rf INCA_libs waves.shm .simvision
	@rm -f ncverilog.history tx.txt rxp.txt rxn.txt ncsim.log ncverilog.log
