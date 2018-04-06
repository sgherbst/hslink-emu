`timescale 1ns/1ps

import time_package::*;
import signal_package::*;

module dut(
    input wire SYSCLK_P,
    input wire SYSCLK_N,
    output reg sim_done = 1'b0
);
    wire clk_orig;
    clkgen clkgen_i(.SYSCLK_P(SYSCLK_P), .SYSCLK_N(SYSCLK_N), .clk_orig(clk_orig));   

    TIME_FORMAT time_in [0:1];
    TIME_FORMAT time_curr;
    TIME_FORMAT time_next;

    wire out_tx, out_rx, clk_tx, clk_rx_p, clk_rx_n, time_eq_tx, time_eq_rx, up, dn;
    FILTER_IN_FORMAT sig_tx;
    FILTER_OUT_FORMAT sig_rx;

    // create system clock
    wire clk_sys;
    clkgate clkgate_i(.clk(clk_orig), .gated(clk_sys), .en(1'b1));
    
    // create TX clock
    const_clock #(.INC(TX_INC), .TIME_WIDTH(TIME_WIDTH)) tx_clk_i(.clk_orig(clk_orig), .clk_sys(clk_sys), .time_next(time_next), .time_clock(time_in[0]), .clk_out(clk_tx), .time_eq(time_eq_tx));

    // create random data generator
    prbs prbs_i(.clk(clk_tx), .out(out_tx));

    // drive data into channel
    tx_driver #(.width(FILTER_IN_WIDTH), .point(FILTER_IN_POINT)) tx_drv_i(.in(out_tx), .out(sig_tx), .clk(clk_tx));

    // filter data stream according to channel + CTLE dynamics
    filter filter_i(.in(sig_tx), .clk_in(clk_tx), .time_eq_in(time_eq_tx), .out(sig_rx_filter), .clk_sys(clk_sys), .time_next(time_next));

    // create RX clock
    const_clock #(.N(2), .INC(RX_INC), .TIME_WIDTH(TIME_WIDTH)) rx_clk_i(.clk_orig(clk_orig), .clk_sys(clk_sys), .time_next(time_next), .time_clock(time_in[1]), .clk_out(clk_rx), .time_eq(time_eq_rx));

    // create time manager
    time_manager #(.N(2)) tm(.time_in(time_in), .time_next(time_next), .time_curr(time_curr), .clk_sys(clk_sys));

    // monitor signals
    adc #(.name("tx"), .time_bits(TIME_WIDTH), .time_point(TIME_POINT), .sig_bits(FILTER_IN_WIDTH), .sig_point(FILTER_IN_POINT)) adc_tx(.clk(clk_tx), .time_curr(time_curr), .sig(sig_tx));
    adc #(.name("rxp"), .time_bits(TIME_WIDTH), .time_point(TIME_POINT), .sig_bits(FILTER_OUT_WIDTH), .sig_point(FILTER_OUT_POINT)) adc_rxp(.clk(clk_rx_p), .time_curr(time_curr), .sig(sig_rx));
    adc #(.name("rxn"), .time_bits(TIME_WIDTH), .time_point(TIME_POINT), .sig_bits(FILTER_OUT_WIDTH), .sig_point(FILTER_OUT_POINT)) adc_rxn(.clk(clk_rx_n), .time_curr(time_curr), .sig(sig_rx));

    // monitor time
    always @(posedge clk_sys) begin
        if (time_curr >= TIME_STOP) begin
            sim_done <= 1'b1;
        end else begin
            sim_done <= sim_done;
        end
    end
endmodule
