# configure the trigger condition
set_property CONTROL.TRIGGER_POSITION 0 $ila_1_i
set_property TRIGGER_COMPARE_VALUE eq1'bF $rst_rx_p

# pulse reset
pulse_reset $rst

# arm the ILA
run_hw_ila $ila_1_i

# pulse reset
pulse_reset $rst

# wait for the ILA to capture the waveform
wait_on_hw_ila $ila_1_i

# upload data from the ILA
upload_hw_ila_data $ila_1_i

# write the CSV file
write_hw_ila_data -csv_file -force {../data/iladata.csv} hw_ila_data_2