# 200 MHz system clock
set_property IOSTANDARD LVDS [get_ports SYSCLK_P]
set_property PACKAGE_PIN H9 [get_ports SYSCLK_P]
set_property PACKAGE_PIN G9 [get_ports SYSCLK_N]
set_property IOSTANDARD LVDS [get_ports SYSCLK_N]
create_clock -period 5.000 -name SYSCLK_P -waveform {0.000 2.500} -add [get_ports SYSCLK_P]

# RX filter configuration
# (on DIP switches)
set_property PACKAGE_PIN AB17 [get_ports {rx_setting[0]}]
set_property IOSTANDARD LVCMOS25 [get_ports {rx_setting[0]}]
set_property PACKAGE_PIN AC16 [get_ports {rx_setting[1]}]
set_property IOSTANDARD LVCMOS25 [get_ports {rx_setting[1]}]
#set_property PACKAGE_PIN AC17 [get_ports rx_setting[2]]
#set_property IOSTANDARD LVCMOS25 [get_ports rx_setting[2]]
#set_property PACKAGE_PIN AJ13 [get_ports rx_setting[3]]
#set_property IOSTANDARD LVCMOS25 [get_ports rx_setting[3]]

# TX filter configuration
# (on PMOD 1)
set_property PACKAGE_PIN AA20 [get_ports {tx_setting[0]}]
set_property IOSTANDARD LVCMOS25 [get_ports {tx_setting[0]}]
set_property PACKAGE_PIN AC18 [get_ports {tx_setting[1]}]
set_property IOSTANDARD LVCMOS25 [get_ports {tx_setting[1]}]
set_property PACKAGE_PIN AC19 [get_ports {tx_setting[2]}]
set_property IOSTANDARD LVCMOS25 [get_ports {tx_setting[2]}]
set_property PACKAGE_PIN AB16 [get_ports {tx_setting[3]}]
set_property IOSTANDARD LVCMOS25 [get_ports {tx_setting[3]}]

# output
# (on LED 0)
set_property PACKAGE_PIN A17 [get_ports sim_done]
set_property IOSTANDARD LVCMOS15 [get_ports sim_done]

create_debug_core u_ila_0 ila
set_property ALL_PROBE_SAME_MU true [get_debug_cores u_ila_0]
set_property ALL_PROBE_SAME_MU_CNT 1 [get_debug_cores u_ila_0]
set_property C_ADV_TRIGGER false [get_debug_cores u_ila_0]
set_property C_DATA_DEPTH 1024 [get_debug_cores u_ila_0]
set_property C_EN_STRG_QUAL false [get_debug_cores u_ila_0]
set_property C_INPUT_PIPE_STAGES 0 [get_debug_cores u_ila_0]
set_property C_TRIGIN_EN false [get_debug_cores u_ila_0]
set_property C_TRIGOUT_EN false [get_debug_cores u_ila_0]
set_property port_width 1 [get_debug_ports u_ila_0/clk]
connect_debug_port u_ila_0/clk [get_nets [list clkgen_i/clk_wiz_0_i/inst/clk_out1]]
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe0]
set_property port_width 22 [get_debug_ports u_ila_0/probe0]
connect_debug_port u_ila_0/probe0 [get_nets [list {adc_rxn/time_samp[0]} {adc_rxn/time_samp[1]} {adc_rxn/time_samp[2]} {adc_rxn/time_samp[3]} {adc_rxn/time_samp[4]} {adc_rxn/time_samp[5]} {adc_rxn/time_samp[6]} {adc_rxn/time_samp[7]} {adc_rxn/time_samp[8]} {adc_rxn/time_samp[9]} {adc_rxn/time_samp[10]} {adc_rxn/time_samp[11]} {adc_rxn/time_samp[12]} {adc_rxn/time_samp[13]} {adc_rxn/time_samp[14]} {adc_rxn/time_samp[15]} {adc_rxn/time_samp[16]} {adc_rxn/time_samp[17]} {adc_rxn/time_samp[18]} {adc_rxn/time_samp[19]} {adc_rxn/time_samp[20]} {adc_rxn/time_samp[21]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe1]
set_property port_width 23 [get_debug_ports u_ila_0/probe1]
connect_debug_port u_ila_0/probe1 [get_nets [list {adc_rxn/sig_samp[0]} {adc_rxn/sig_samp[1]} {adc_rxn/sig_samp[2]} {adc_rxn/sig_samp[3]} {adc_rxn/sig_samp[4]} {adc_rxn/sig_samp[5]} {adc_rxn/sig_samp[6]} {adc_rxn/sig_samp[7]} {adc_rxn/sig_samp[8]} {adc_rxn/sig_samp[9]} {adc_rxn/sig_samp[10]} {adc_rxn/sig_samp[11]} {adc_rxn/sig_samp[12]} {adc_rxn/sig_samp[13]} {adc_rxn/sig_samp[14]} {adc_rxn/sig_samp[15]} {adc_rxn/sig_samp[16]} {adc_rxn/sig_samp[17]} {adc_rxn/sig_samp[18]} {adc_rxn/sig_samp[19]} {adc_rxn/sig_samp[20]} {adc_rxn/sig_samp[21]} {adc_rxn/sig_samp[22]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe2]
set_property port_width 22 [get_debug_ports u_ila_0/probe2]
connect_debug_port u_ila_0/probe2 [get_nets [list {adc_rxp/time_samp[0]} {adc_rxp/time_samp[1]} {adc_rxp/time_samp[2]} {adc_rxp/time_samp[3]} {adc_rxp/time_samp[4]} {adc_rxp/time_samp[5]} {adc_rxp/time_samp[6]} {adc_rxp/time_samp[7]} {adc_rxp/time_samp[8]} {adc_rxp/time_samp[9]} {adc_rxp/time_samp[10]} {adc_rxp/time_samp[11]} {adc_rxp/time_samp[12]} {adc_rxp/time_samp[13]} {adc_rxp/time_samp[14]} {adc_rxp/time_samp[15]} {adc_rxp/time_samp[16]} {adc_rxp/time_samp[17]} {adc_rxp/time_samp[18]} {adc_rxp/time_samp[19]} {adc_rxp/time_samp[20]} {adc_rxp/time_samp[21]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe3]
set_property port_width 23 [get_debug_ports u_ila_0/probe3]
connect_debug_port u_ila_0/probe3 [get_nets [list {adc_rxp/sig_samp[0]} {adc_rxp/sig_samp[1]} {adc_rxp/sig_samp[2]} {adc_rxp/sig_samp[3]} {adc_rxp/sig_samp[4]} {adc_rxp/sig_samp[5]} {adc_rxp/sig_samp[6]} {adc_rxp/sig_samp[7]} {adc_rxp/sig_samp[8]} {adc_rxp/sig_samp[9]} {adc_rxp/sig_samp[10]} {adc_rxp/sig_samp[11]} {adc_rxp/sig_samp[12]} {adc_rxp/sig_samp[13]} {adc_rxp/sig_samp[14]} {adc_rxp/sig_samp[15]} {adc_rxp/sig_samp[16]} {adc_rxp/sig_samp[17]} {adc_rxp/sig_samp[18]} {adc_rxp/sig_samp[19]} {adc_rxp/sig_samp[20]} {adc_rxp/sig_samp[21]} {adc_rxp/sig_samp[22]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe4]
set_property port_width 22 [get_debug_ports u_ila_0/probe4]
connect_debug_port u_ila_0/probe4 [get_nets [list {adc_tx/time_samp[0]} {adc_tx/time_samp[1]} {adc_tx/time_samp[2]} {adc_tx/time_samp[3]} {adc_tx/time_samp[4]} {adc_tx/time_samp[5]} {adc_tx/time_samp[6]} {adc_tx/time_samp[7]} {adc_tx/time_samp[8]} {adc_tx/time_samp[9]} {adc_tx/time_samp[10]} {adc_tx/time_samp[11]} {adc_tx/time_samp[12]} {adc_tx/time_samp[13]} {adc_tx/time_samp[14]} {adc_tx/time_samp[15]} {adc_tx/time_samp[16]} {adc_tx/time_samp[17]} {adc_tx/time_samp[18]} {adc_tx/time_samp[19]} {adc_tx/time_samp[20]} {adc_tx/time_samp[21]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe5]
set_property port_width 16 [get_debug_ports u_ila_0/probe5]
connect_debug_port u_ila_0/probe5 [get_nets [list {adc_tx/sig_samp[0]} {adc_tx/sig_samp[1]} {adc_tx/sig_samp[2]} {adc_tx/sig_samp[3]} {adc_tx/sig_samp[4]} {adc_tx/sig_samp[5]} {adc_tx/sig_samp[6]} {adc_tx/sig_samp[7]} {adc_tx/sig_samp[8]} {adc_tx/sig_samp[9]} {adc_tx/sig_samp[10]} {adc_tx/sig_samp[11]} {adc_tx/sig_samp[12]} {adc_tx/sig_samp[13]} {adc_tx/sig_samp[14]} {adc_tx/sig_samp[15]}]]
set_property C_CLK_INPUT_FREQ_HZ 300000000 [get_debug_cores dbg_hub]
set_property C_ENABLE_CLK_DIVIDER false [get_debug_cores dbg_hub]
set_property C_USER_SCAN_CHAIN 1 [get_debug_cores dbg_hub]
connect_debug_port dbg_hub/clk [get_nets clk_sys]
