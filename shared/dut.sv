`timescale 1ns/1ps

import time_package::*;
import signal_package::*;
import filter_package::*;
import tx_package::*;

module dut(
    input wire rst,
    input wire [TX_SETTING_WIDTH-1:0] tx_setting,
    input wire [RX_SETTING_WIDTH-1:0] rx_setting,
    output wire sim_done,

    input wire SYSCLK_P,
    input wire SYSCLK_N
);
    // Clock generation code
    wire cke_tx, cke_rx_p, cke_rx_n;
    wire clk_sys, clk_tx, clk_rx_p, clk_rx_n;
    clkgen clkgen_i(.SYSCLK_P(SYSCLK_P),
                    .SYSCLK_N(SYSCLK_N), 
                    .clk_sys(clk_sys),
                    .clk_tx(clk_tx),
                    .cke_tx(cke_tx),
                    .clk_rx_p(clk_rx_p),
                    .cke_rx_p(cke_rx_p),
                    .clk_rx_n(clk_rx_n),
                    .cke_rx_n(cke_rx_n));   

    // Reset generator
    reg rst_sys;
    always @(posedge clk_sys) begin
        if (rst == 1'b1) begin
            rst_sys <= 1'b1;
        end else begin
            rst_sys <= 1'b0;
        end
    end
    
    reg rst_tx;
    always @(posedge clk_sys) begin
        if (rst == 1'b1) begin
            rst_tx <= 1'b1;
        end else if (cke_tx == 1'b1) begin
            rst_tx <= 1'b0;
        end else begin
            rst_tx <= rst_tx;
        end
    end

    // Time management signals
    TIME_FORMAT time_in [0:1];
    TIME_FORMAT time_curr;
    TIME_FORMAT time_next;
    wire time_eq_tx, time_eq_rx;

    // Representation of TX and RX data signals
    wire out_tx, out_rx;
    FILTER_IN_FORMAT sig_tx;
    FILTER_OUT_FORMAT sig_rx;
    
    // create TX clock
    const_clock #(.INC(TX_INC)) tx_clk_i(.clk(clk_sys),
                                         .rst(rst_sys),
                                         .time_next(time_next),
                                         .time_clock(time_in[0]),
                                         .cke_out(cke_tx),
                                         .time_eq(time_eq_tx));

    // create random data generator
    prbs prbs_i(.out(out_tx),
                .clk(clk_tx),
                .rst(rst_tx));

    // drive data into channel
    tx_ffe tx_ffe_i(.in(out_tx),
                    .out(sig_tx),
                    .tx_setting(tx_setting),
                    .clk(clk_tx),
                    .rst(rst_tx));

    // filter data stream according to channel + CTLE dynamics
    filter filter_i(.in(sig_tx),
                    .time_eq_in(time_eq_tx),
                    .out(sig_rx),
                    .time_next(time_next),
                    .rx_setting(rx_setting),
                    .clk(clk_sys),
                    .rst(rst_sys));

    // create RX clock
    const_clock #(.N(2), 
                  .INC(RX_INC)) rx_clk_i(.time_next(time_next),
                                         .time_clock(time_in[1]),
                                         .cke_out({cke_rx_p, cke_rx_n}),
                                         .time_eq(time_eq_rx),
                                         .clk(clk_sys),
                                         .rst(rst_sys));

    // create time manager
    time_manager #(.N(2)) tm(.time_in(time_in),
                             .time_next(time_next),
                             .time_curr(time_curr),
                             .clk(clk_sys),
                             .rst(rst_sys));

    // TX signal monitor
    adc #(.name("tx"),
          .sig_bits(FILTER_IN_WIDTH), 
          .sig_point(FILTER_IN_POINT)) adc_tx(.clk(clk_tx),
                                              .time_curr(time_curr),
                                              .sig(sig_tx));
                                              
    // RX rising edge signal monitor
    adc #(.name("rxp"),
          .sig_bits(FILTER_OUT_WIDTH),
          .sig_point(FILTER_OUT_POINT)) adc_rxp(.clk(clk_rx_p),
                                                .time_curr(time_curr),
                                                .sig(sig_rx));
    
    // RX falling edge signal monitor                              
    adc #(.name("rxn"),
          .sig_bits(FILTER_OUT_WIDTH),
          .sig_point(FILTER_OUT_POINT)) adc_rxn(.clk(clk_rx_n),
                                                .time_curr(time_curr),
                                                .sig(sig_rx));

    // monitor time
    reg sim_done_reg;
    assign sim_done = sim_done_reg;
    always @(posedge clk_sys) begin
        if (rst == 1'b1) begin
            sim_done_reg <= 1'b0;
        end else if (time_curr >= TIME_STOP) begin
            sim_done_reg <= 1'b1;
        end else begin
            sim_done_reg <= sim_done;
        end
    end
endmodule
