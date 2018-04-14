# 200 MHz system clock
set_property IOSTANDARD LVDS [get_ports SYSCLK_P]
set_property PACKAGE_PIN H9 [get_ports SYSCLK_P]
set_property PACKAGE_PIN G9 [get_ports SYSCLK_N]
set_property IOSTANDARD LVDS [get_ports SYSCLK_N]
create_clock -period 5.000 -name SYSCLK_P -waveform {0.000 2.500} -add [get_ports SYSCLK_P]

# output		
# (on LED 0)		
set_property PACKAGE_PIN A17 [get_ports time_flag]		
set_property IOSTANDARD LVCMOS15 [get_ports time_flag]

