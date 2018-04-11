`timescale 1ns/1ps

import tx_package::*;
import filter_package::*;

`ifndef RX_SETTING
    `define RX_SETTING 'd0
`endif

`ifndef TX_SETTING
    `define TX_SETTING 'd10
`endif

`ifndef USE_ADC
    `define USE_ADC 0
`endif

module tb;
    wire [RX_SETTING_WIDTH-1:0] rx_setting = `RX_SETTING;
    wire [TX_SETTING_WIDTH-1:0] tx_setting = `TX_SETTING;

    wire sim_done;
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

    dut #(.USE_VIO(0),
          .USE_ADC(`USE_ADC)) dut_i(
              .SYSCLK_P(SYSCLK_P),    
              .SYSCLK_N(SYSCLK_N),
              .sim_done(sim_done),
              .tx_setting_ext(tx_setting),
              .rx_setting_ext(rx_setting),
              .rst_ext(rst));

    always @(sim_done) begin
        if (sim_done == 1'b1) begin
            $finish;
        end
    end
endmodule
