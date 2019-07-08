# create the Vivado project
create_project -force project ../build/project

# source files
add_files [glob ../build/*.sv]
add_files [glob ../cpu/*.sv]
add_files [glob ../shared/*.sv]
add_files [glob sim.sv]

# defines
set_property -name verilog_define -value [list \
    [lindex $argv 3] \
    PWL_OVFL_CHK \
    RX_SETTING=[lindex $argv 0] \
    START_TIME=[lindex $argv 1] \
    STOP_TIME=[lindex $argv 2] \
] -objects [get_filesets {sim_1 sources_1}]

# set the top-level module
set_property -name top -value tb -objects [get_filesets {sim_1 sources_1}]

# set the simulation runtime
set_property -name xsim.simulate.runtime -value -all -objects [get_fileset sim_1]

# run the simulation
launch_simulation
