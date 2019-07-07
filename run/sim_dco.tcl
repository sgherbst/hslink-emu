# create the Vivado project
create_project -force project ../build/project

# source files
add_files [glob ../build/*.sv]
add_files [glob ../cpu/*.sv]
add_files [glob ../shared/*.sv]
add_files [glob sim_dco.sv]

# defines
set_property -name verilog_define -value [list \
    SIM_DEBUG \
    PWL_OVFL_CHK \
] -objects [get_filesets {sim_1 sources_1}]

# set the top-level module
set_property -name top -value top -objects [get_filesets {sim_1 sources_1}]

# set the simulation runtime
set_property -name xsim.simulate.runtime -value -all -objects [get_fileset sim_1]

# run the simulation
launch_simulation
