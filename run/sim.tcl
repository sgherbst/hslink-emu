# create the Vivado project
create_project -force project ../build/project

# source files
add_files [glob ../build/*.sv]
add_files [glob ../cpu/*.sv]
add_files [glob ../shared/*.sv]
add_files [glob sim.sv]

# defines
set_property -name verilog_define -value [list \
    SIM_DEBUG \
    RX_SETTING=4 \
    TX_SETTING=4 \
    KP_LF=256 \
    KI_LF=1 \
    DCO_CODE_INIT=6700 \
    TIME_TRIG=18014398 \
    JITTER_SCALE_RX=700 \
    JITTER_SCALE_TX=700 \
    PWL_OVFL_CHK \
] -objects [get_filesets {sim_1 sources_1}]

# set the top-level module
set_property -name top -value tb -objects [get_filesets {sim_1 sources_1}]

# set the simulation runtime
set_property -name xsim.simulate.runtime -value -all -objects [get_fileset sim_1]

# run the simulation
launch_simulation
