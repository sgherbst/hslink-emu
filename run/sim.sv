`timescale 1ns/1ps

import tx_package::*;
import filter_package::*;
import time_package::*;

// Default settings for Vivado

`ifndef RX_SETTING
    `define RX_SETTING 'd0
`endif

`ifndef TX_SETTING
    `define TX_SETTING 'd10
`endif

`ifndef DCO_CODE_INIT
    `define DCO_CODE_INIT 'd7882
`endif

`ifndef KP_LF
    `define KP_LF 'd256
`endif

`ifndef KI_LF
    `define KI_LF 'd1
`endif

`ifndef USE_ADC
    `define USE_ADC 0
`endif

module tb;
    wire [RX_SETTING_WIDTH-1:0] rx_setting = `RX_SETTING;
    wire [TX_SETTING_WIDTH-1:0] tx_setting = `TX_SETTING;
    wire [DCO_CODE_WIDTH-1:0] dco_init = `DCO_CODE_INIT;
    wire signed [DCO_CODE_WIDTH-1:0] kp_lf = `KP_LF;
    wire signed [DCO_CODE_WIDTH-1:0] ki_lf = `KI_LF;

    wire TIME_FORMAT time_trig = TIME_STOP;
    wire time_flag;

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
    
    reg rst = 1'b1;
    initial begin
        #1000;
        rst = 1'b0;
    end

    dut #(
        .USE_VIO(0),
        .USE_ADC(`USE_ADC)
    ) dut_i(
        .SYSCLK_P(SYSCLK_P),    
        .SYSCLK_N(SYSCLK_N),
        .rst_ext(rst),
        .rx_setting_ext(rx_setting),
        .tx_setting_ext(tx_setting),
        .dco_init_ext(dco_init),
        .kp_lf_ext(kp_lf),
        .ki_lf_ext(ki_lf),
        .time_trig_ext(time_trig),
        .time_flag(time_flag)
    );

    always @(time_flag) begin
        if (time_flag == 1'b1) begin
            $finish;
        end
    end
endmodule
