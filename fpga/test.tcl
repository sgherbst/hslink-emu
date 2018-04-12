# connect to hardware
connect_hw_server
open_hw_target

# set bit files
set_property PROBES.FILE {C:/Users/sgherbst/FPGA_Projects/msemu/msemu.runs/impl_1/debug_nets.ltx} [lindex [get_hw_devices xc7z045_1] 0]
set_property PROGRAM.FILE {C:/Users/sgherbst/FPGA_Projects/msemu/msemu.runs/impl_1/dut.bit} [lindex [get_hw_devices xc7z045_1] 0]

# program device
program_hw_devices [lindex [get_hw_devices xc7z045_1] 0]
refresh_hw_device [lindex [get_hw_devices xc7z045_1] 0]

# initial display of ILA (is this necessary?)
display_hw_ila_data [ get_hw_ila_data hw_ila_data_1 -of_objects [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"u_ila_0"}]]

# set radix of VIOs
set_property OUTPUT_VALUE_RADIX BINARY [get_hw_probes rst]
set_property OUTPUT_VALUE_RADIX UNSIGNED [get_hw_probes rx_setting]
set_property OUTPUT_VALUE_RADIX UNSIGNED [get_hw_probes tx_setting]

# set up triggering
set_property TRIGGER_COMPARE_VALUE eq1'bF [get_hw_probes rst_sys -of_objects [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"u_ila_0"}]]

for { set rx_setting 0}  {$rx_setting <= 3} {incr rx_setting} {
	for { set tx_setting 0} {$tx_setting <= 10} {incr tx_setting} {
		puts "$rx_setting, $tx_setting"

		# set the trigger
		run_hw_ila [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"u_ila_0"}]

		# set RX
		set_property OUTPUT_VALUE $rx_setting [get_hw_probes rx_setting -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		commit_hw_vio [get_hw_probes {rx_setting} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]

		# set TX
		set_property OUTPUT_VALUE $tx_setting [get_hw_probes tx_setting -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		commit_hw_vio [get_hw_probes {tx_setting} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]

		# pulse reset
		set_property OUTPUT_VALUE 1 [get_hw_probes rst -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		commit_hw_vio [get_hw_probes {rst} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]

		set_property OUTPUT_VALUE 0 [get_hw_probes rst -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		commit_hw_vio [get_hw_probes {rst} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]

		# wait for trigger
		wait_on_hw_ila [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"u_ila_0"}]
		display_hw_ila_data [upload_hw_ila_data [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"u_ila_0"}]]

		# make sure that radix is set properly
		set_property DISPLAY_RADIX SIGNED [get_hw_probes sig_tx]
		set_property DISPLAY_RADIX SIGNED [get_hw_probes sig_rx]
		set_property DISPLAY_RADIX UNSIGNED [get_hw_probes time_curr]

		# write the data
		set file_name "\\\\Mac\\Home\\Desktop\\msemu\\data\\ila\\${rx_setting}_${tx_setting}.csv"
		write_hw_ila_data -csv_file -force $file_name hw_ila_data_1
	}
}

# disconnect
disconnect_hw_server localhost:3121