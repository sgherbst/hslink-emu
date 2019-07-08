`timescale 1ns/1ps

import tx_package::*;
import filter_package::*;
import time_package::*;

// Default settings for Vivado

module tb;

    // set up waveform probing

    initial begin
        `ifdef SIM_DEBUG
            $dumpvars(0, tb);
        `elsif SIM_LEAN
            $dumpvars(0, dut_i.dco_code);
            $dumpvars(0, dut_i.run_state);
            $dumpvars(0, dut_i.time_curr);
            $dumpvars(0, dut_i.loopback_test_i);
        `elsif SIM_PROFILE
        `endif
    end

    // generate differential clock
    
    reg SYSCLK_P = 1'b0;
    reg SYSCLK_N = 1'b1;

    initial begin
        forever begin
            SYSCLK_P = 1'b0;
            SYSCLK_N = 1'b1;
            #2.5;
            SYSCLK_P = 1'b1;
            SYSCLK_N = 1'b0;
            #2.5;
        end
    end
    
    // generate reset

    reg rst = 1'b1;
    initial begin
        #3000;
        rst = 1'b0;
    end

    // monitor running state to see when the emulation has finished

    // TODO: move to a package
    localparam [2:0] IN_RESET   =   3'b100;
    localparam [2:0] WAITING    =   3'b000;
    localparam [2:0] RUNNING    =   3'b010;
    localparam [2:0] DONE       =   3'b001;

    wire [2:0] run_state;
    always @(run_state) begin
        case (run_state)
            IN_RESET: $display("IN_RESET");
            WAITING: $display("WAITING");
            RUNNING: $display("RUNNING");
            DONE: begin
                $display("DONE");
                $finish;
            end
        endcase
    end

    // I/O set by VIO on the FPGA

    // RX CTLE setting

    `ifndef RX_SETTING
        `define RX_SETTING 'd4
    `endif

    wire [RX_SETTING_WIDTH-1:0] rx_setting = `RX_SETTING;

    // TX FFE setting

    `ifndef TX_SETTING
        `define TX_SETTING 'd4
    `endif

    wire [TX_SETTING_WIDTH-1:0] tx_setting = `TX_SETTING;

    // Initial DCO code

    `ifndef DCO_CODE_INIT
//        `define DCO_CODE_INIT 'd6700
        `define DCO_CODE_INIT 'd8192
    `endif

    wire [DCO_CODE_WIDTH-1:0] dco_init = `DCO_CODE_INIT;
    
    // Proportional gain of digital loop filter

    `ifndef KP_LF
        `define KP_LF 'd256
    `endif

    wire signed [DCO_CODE_WIDTH-1:0] kp_lf = `KP_LF;

    // Integral gain of digital loop filter

    `ifndef KI_LF
        `define KI_LF 'd1
    `endif

    wire signed [DCO_CODE_WIDTH-1:0] ki_lf = `KI_LF;

    // Scale factor on jitter of TX clock

    `ifndef JITTER_SCALE_TX
//        `define JITTER_SCALE_TX 'd700
        `define JITTER_SCALE_TX 'd0
    `endif

    TX_JITTER_SCALE_FORMAT jitter_scale_tx = `JITTER_SCALE_TX;

    // Scale factor on jitter of RX clock

    `ifndef JITTER_SCALE_RX
//        `define JITTER_SCALE_RX 'd700
        `define JITTER_SCALE_RX 'd0
    `endif

    RX_JITTER_SCALE_FORMAT jitter_scale_rx = `JITTER_SCALE_RX;

    // start_time is used to indicate when the
    // loopback tester should start recording

    `ifndef START_TIME
//        `define START_TIME 0
        `define START_TIME 144115188
    `endif
    wire TIME_FORMAT start_time = `START_TIME;

    // For CPU simulation, stop_time is used to
    // indicate the end of simulation.  On the
    // FPGA, this signal is used for triggering
    // debug cores.

    `ifndef STOP_TIME
        // `define STOP_TIME 18014398 // 128 ns
        `define STOP_TIME 288230376 // 2.048 us
    `endif
    wire TIME_FORMAT stop_time = `STOP_TIME;

    // loopback_offset indicates the delay between transmitted
    // TX bits and received RX bits

    `ifndef LOOPBACK_OFFSET
        `define LOOPBACK_OFFSET 35
    `endif
    wire [7:0] loopback_offset = `LOOPBACK_OFFSET;

    dut #(
        .USE_VIO(0)
    ) dut_i (
        // differential clock
        .SYSCLK_P(SYSCLK_P),    
        .SYSCLK_N(SYSCLK_N),

        // reset signal
        .rst_ext(rst),

        // time flag used here to indicate
        // end of emulation
        .run_state(run_state),

        // I/O normally controlled by VIO
        .rx_setting_ext(rx_setting),
        .tx_setting_ext(tx_setting),
        .dco_init_ext(dco_init),
        .kp_lf_ext(kp_lf),
        .ki_lf_ext(ki_lf),
        .start_time_ext(start_time),
        .stop_time_ext(stop_time),
        .loopback_offset_ext(loopback_offset),
        .jitter_scale_tx_ext(jitter_scale_tx),
        .jitter_scale_rx_ext(jitter_scale_rx)
    );

endmodule
