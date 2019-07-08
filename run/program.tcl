# code to program the device

set bit_file {../build/project/project.runs/impl_1/dut.bit}
set probe_file {../build/project/project.runs/impl_1/dut.ltx}

open_hw
connect_hw_server
open_hw_target

set hw_device [get_hw_devices *xc7z045*]
current_hw_device $hw_device
refresh_hw_device $hw_device

set_property PROGRAM.FILE $bit_file $hw_device
set_property PROBES.FILE $probe_file $hw_device
set_property FULL_PROBES.FILE $probe_file $hw_device

program_hw_devices $hw_device
refresh_hw_device $hw_device

# other useful initialization

# ILA aliases

set ila_0_i [get_hw_ilas -of_objects $hw_device -filter {CELL_NAME=~"ila_0_i"}]
set ila_1_i [get_hw_ilas -of_objects $hw_device -filter {CELL_NAME=~"ila_1_i"}]
set ila_2_i [get_hw_ilas -of_objects $hw_device -filter {CELL_NAME=~"ila_2_i"}]

set rst_rx_p [get_hw_probes rst_rx_p -of_objects $ila_1_i]
set time_curr_2 [get_hw_probes time_curr_2 -of_objects $ila_1_i]
set dco_code [get_hw_probes dco_code -of_objects $ila_1_i]

# VIO aliases

set vio_0_i [get_hw_vios -of_objects $hw_device -filter {CELL_NAME=~"vio_0_i"}]

set rst [get_hw_probes rst -of_objects $vio_0_i]
set rx_bad_bits [get_hw_probes rx_bad_bits -of_objects $vio_0_i]
set rx_good_bits [get_hw_probes rx_good_bits -of_objects $vio_0_i]
set rx_total_bits [get_hw_probes rx_total_bits -of_objects $vio_0_i]
set dco_init [get_hw_probes dco_init -of_objects $vio_0_i]
set start_time [get_hw_probes start_time -of_objects $vio_0_i]
set stop_time [get_hw_probes stop_time -of_objects $vio_0_i]
set loopback_offset [get_hw_probes loopback_offset -of_objects $vio_0_i]
set ki_lf [get_hw_probes ki_lf -of_objects $vio_0_i]
set kp_lf [get_hw_probes kp_lf -of_objects $vio_0_i]

# turn off auto-refresh

set_property CORE_REFRESH_RATE_MS 0 $ila_0_i
set_property CORE_REFRESH_RATE_MS 0 $ila_1_i
set_property CORE_REFRESH_RATE_MS 0 $ila_2_i
set_property CORE_REFRESH_RATE_MS 0 $vio_0_i

# ILA configuration

set_property DISPLAY_RADIX UNSIGNED $time_curr_2
set_property DISPLAY_RADIX UNSIGNED $dco_code

# VIO configuration

set_property INPUT_VALUE_RADIX UNSIGNED $rx_bad_bits
set_property INPUT_VALUE_RADIX UNSIGNED $rx_good_bits
set_property INPUT_VALUE_RADIX UNSIGNED $rx_total_bits
set_property OUTPUT_VALUE_RADIX UNSIGNED $dco_init
set_property OUTPUT_VALUE_RADIX UNSIGNED $start_time
set_property OUTPUT_VALUE_RADIX UNSIGNED $stop_time
set_property OUTPUT_VALUE_RADIX UNSIGNED $loopback_offset
set_property OUTPUT_VALUE_RADIX UNSIGNED $ki_lf
set_property OUTPUT_VALUE_RADIX UNSIGNED $kp_lf

# utility functions

proc pulse_reset {reset} {
	set_property OUTPUT_VALUE 1 $reset
	commit_hw_vio $reset
	set_property OUTPUT_VALUE 0 $reset
	commit_hw_vio $reset
}
