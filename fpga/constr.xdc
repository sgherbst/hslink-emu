# 200 MHz system clock

set_property IOSTANDARD LVDS [get_ports SYSCLK_P]
set_property PACKAGE_PIN H9 [get_ports SYSCLK_P]
set_property PACKAGE_PIN G9 [get_ports SYSCLK_N]
set_property IOSTANDARD LVDS [get_ports SYSCLK_N]
create_clock -period 5.000 -name SYSCLK_P -waveform {0.000 2.500} -add [get_ports SYSCLK_P]

# Debug hub clock

set_property C_ENABLE_CLK_DIVIDER false [get_debug_cores dbg_hub]
set_property C_USER_SCAN_CHAIN 1 [get_debug_cores dbg_hub]
set_property C_CLK_INPUT_FREQ_HZ 30000000 [get_debug_cores dbg_hub]
connect_debug_port dbg_hub/clk [get_nets clkgen_i/clk_wiz_0_i/clk_out1]

# output		
# (on LED 0)		
set_property PACKAGE_PIN A17 [get_ports time_flag]		
set_property IOSTANDARD LVCMOS15 [get_ports time_flag]

