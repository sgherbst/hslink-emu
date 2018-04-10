`timescale 1ns/1ps

import tx_package::*;
import filter_package::*;

`ifndef RX_SETTING
    `define RX_SETTING 'd0
`endif

`ifndef TX_SETTING
    `define TX_SETTING 'd10
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

    dut dut_i(.SYSCLK_P(SYSCLK_P),    
              .SYSCLK_N(SYSCLK_N),
              .sim_done(sim_done),
              .tx_setting(tx_setting),
              .rx_setting(rx_setting));

    always @(sim_done) begin
        if (sim_done == 1'b1) begin
            $finish;
        end
    end
endmodule
