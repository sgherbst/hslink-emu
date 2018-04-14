##############
# Trigger setup
##############

set_property TRIGGER_COMPARE_VALUE eq1'bF [get_hw_probes rst_tx -of_objects [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_0_i"}]]
set_property TRIGGER_COMPARE_VALUE eq1'bF [get_hw_probes rst_rx_p -of_objects [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_1_i"}]]
set_property TRIGGER_COMPARE_VALUE eq1'bF [get_hw_probes rst_rx_n -of_objects [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_2_i"}]]

##############
# Radix setup
##############

# TX probes
set_property DISPLAY_RADIX SIGNED [get_hw_probes filter_in]
set_property DISPLAY_RADIX UNSIGNED [get_hw_probes time_curr]

# RX P probes
set_property DISPLAY_RADIX SIGNED [get_hw_probes filter_out_1]
set_property DISPLAY_RADIX SIGNED [get_hw_probes comp_in]
set_property DISPLAY_RADIX SIGNED [get_hw_probes dfe_out]
set_property DISPLAY_RADIX UNSIGNED [get_hw_probes time_curr_1]

# RX N probes
set_property DISPLAY_RADIX SIGNED [get_hw_probes filter_out]
set_property DISPLAY_RADIX UNSIGNED [get_hw_probes time_curr_2]

for { set rx_setting 0}  {$rx_setting <= 15} {incr rx_setting} {
	for { set tx_setting 0} {$tx_setting <= 9} {incr tx_setting} {
		puts "$rx_setting, $tx_setting"

		# pulse reset
		startgroup
		set_property OUTPUT_VALUE 1 [get_hw_probes rst -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		commit_hw_vio [get_hw_probes {rst} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		endgroup

		startgroup
		set_property OUTPUT_VALUE 0 [get_hw_probes rst -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		commit_hw_vio [get_hw_probes {rst} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		endgroup

		# set the triggers
		run_hw_ila [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_0_i"}]
		run_hw_ila [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_1_i"}]
		run_hw_ila [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_2_i"}]

		# set RX
		set_property OUTPUT_VALUE $rx_setting [get_hw_probes rx_setting -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		commit_hw_vio [get_hw_probes {rx_setting} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]

		# set TX
		set_property OUTPUT_VALUE $tx_setting [get_hw_probes tx_setting -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		commit_hw_vio [get_hw_probes {tx_setting} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]

		# pulse reset
		startgroup
		set_property OUTPUT_VALUE 1 [get_hw_probes rst -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		commit_hw_vio [get_hw_probes {rst} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		endgroup

		startgroup
		set_property OUTPUT_VALUE 0 [get_hw_probes rst -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		commit_hw_vio [get_hw_probes {rst} -of_objects [get_hw_vios -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"vio_0_i"}]]
		endgroup

		# get data
		wait_on_hw_ila [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_0_i"}]\
		  [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_1_i"}]\
		  [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_2_i"}]
		display_hw_ila_data [upload_hw_ila_data [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_0_i"}]]
		display_hw_ila_data [upload_hw_ila_data [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_1_i"}]]
		display_hw_ila_data [upload_hw_ila_data [get_hw_ilas -of_objects [get_hw_devices xc7z045_1] -filter {CELL_NAME=~"ila_2_i"}]]

		# make the directory
		set path "\\\\Mac\\Home\\Desktop\\msemu\\data\\ila\\sweep\\${rx_setting}_${tx_setting}"
		file mkdir $path

		# write the data
		set file_name "${path}\\ila_0_data.csv"
		write_hw_ila_data -csv_file -force $file_name hw_ila_data_1

		set file_name "${path}\\ila_1_data.csv"
		write_hw_ila_data -csv_file -force $file_name hw_ila_data_2

		set file_name "${path}\\ila_2_data.csv"
		write_hw_ila_data -csv_file -force $file_name hw_ila_data_3	
	}
}