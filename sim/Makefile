# Makefile for running simulation

# system settings
RX_FREQ_MIN := 7.5e9
RX_FREQ_MAX := 8.5e9
RX_FREQ_INIT := 8e9
TX_FREQ := 8e9
RX_DELAY := 0
TX_DELAY := 0

# V2 settings
NUM_UI = 22
SIG_RES = 1e-4
PWL_RES = 1e-5
TABLE_ENTRIES = 1024
TIME_RES := 1e-13
RX_PRESET := 7
TX_PRESET := 7

# V3 settings
SIM_TIME_SHORT = 25e-9
SIM_TIME_LONG = 2e-6
DCO_BITS = 14
KP_LF = 256
KI_LF = 1
NUM_DFE_TAPS = 2
DCO_TABLE_ENTRIES = 1024

# default rule:
all: short

PYTHON = python3
SCRIPT = run.py

COMMON_ARGS = --sig_res $(SIG_RES) --table_entries $(TABLE_ENTRIES) --time_res $(TIME_RES) --rx_preset $(RX_PRESET) --tx_preset $(TX_PRESET) --rx_freq_min $(RX_FREQ_MIN) --rx_freq_max $(RX_FREQ_MAX) --rx_freq_init $(RX_FREQ_INIT) --tx_freq $(TX_FREQ) --rx_delay $(RX_DELAY) --tx_delay $(TX_DELAY) --num_ui $(NUM_UI) --pwl_res $(PWL_RES) --dco_bits $(DCO_BITS) --kp_lf $(KP_LF) --ki_lf $(KI_LF) --num_dfe_taps $(NUM_DFE_TAPS) --dco_table_entries $(DCO_TABLE_ENTRIES)

filter_table:
	@$(PYTHON) $(SCRIPT) --run_mode filter_table --sim_time $(SIM_TIME_SHORT) --show $(COMMON_ARGS)

dco_table:
	@$(PYTHON) $(SCRIPT) --run_mode dco_table --sim_time $(SIM_TIME_SHORT) --show $(COMMON_ARGS)

dfe:
	@$(PYTHON) $(SCRIPT) --run_mode dfe --sim_time $(SIM_TIME_SHORT) --show $(COMMON_ARGS) 

short:
	@$(PYTHON) $(SCRIPT) --run_mode short --sim_time $(SIM_TIME_SHORT) --show $(COMMON_ARGS)

long:
	@$(PYTHON) $(SCRIPT) --run_mode long --sim_time $(SIM_TIME_LONG) --show $(COMMON_ARGS)

clean:
	@rm -rf INCA_libs waves.shm .simvision
	@rm -f ncverilog.history ncverilog.log pwl_emu.txt tx.txt rxp.txt rxn.txt ncsim.log dfe.txt
