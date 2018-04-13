`timescale 1ns/1ps

import tx_package::*;
import filter_package::*;
import time_package::*;

// Default settings for Vivado

module tb;

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
        #1000;
        rst = 1'b0;
    end

    // monitor time flag

    wire time_flag;
    always @(time_flag) begin
        if (time_flag == 1'b1) begin
            $finish;
        end
    end

    // I/O set by VIO on the FPGA

    // RX CTLE setting

    `ifndef RX_SETTING
        `define RX_SETTING 'd0
    `endif

    wire [RX_SETTING_WIDTH-1:0] rx_setting = `RX_SETTING;

    // TX FFE setting

    `ifndef TX_SETTING
        `define TX_SETTING 'd10
    `endif

    wire [TX_SETTING_WIDTH-1:0] tx_setting = `TX_SETTING;

    // Initial DCO code

    `ifndef DCO_CODE_INIT
        `define DCO_CODE_INIT 'd7882
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

    // For CPU simulation, time_trig is used to 
    // indicate the end of simulation.  On the
    // FPGA, this signal is used for triggering
    // debug cores.

    `ifndef TIME_TRIG
        `define TIME_TRIG 2814750
    `endif
    wire TIME_FORMAT time_trig = `TIME_TRIG;

    // If USE_ADC == 1, ADCs are instantiated and certain
    // nodes are probed.  This option should be disabled
    // when profiling CPU simulation or synthesizing 
    // for the FPGA.
    
    `ifndef USE_ADC
        `define USE_ADC 0
    `endif

    dut #(
        .USE_VIO(0),
        .USE_ADC(`USE_ADC)
    ) dut_i (
        // differential clock
        .SYSCLK_P(SYSCLK_P),    
        .SYSCLK_N(SYSCLK_N),

        // reset signal
        .rst_ext(rst),

        // time flag used here to indicate
        // end of emulation
        .time_flag(time_flag),

        // I/O normally controlled by VIO
        .rx_setting_ext(rx_setting),
        .tx_setting_ext(tx_setting),
        .dco_init_ext(dco_init),
        .kp_lf_ext(kp_lf),
        .ki_lf_ext(ki_lf),
        .time_trig_ext(time_trig)
    );

endmodule
