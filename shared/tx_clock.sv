`timescale 1ns/1ps

import time_package::TIME_FORMAT;

module tx_clock #(
    parameter lfsr_init = 2
)(
    input wire clk,
    input wire rst,
    input TIME_FORMAT time_next,
    output TIME_FORMAT time_clock,
    output wire cke_out,
    output wire time_eq
);
    // represent period
    wire [TX_PERIOD_WIDTH-1:0] period = TX_PERIOD_VAL;

    // instantiate the clock
    clock #(
        .N(1),
        .PERIOD_WIDTH(TX_PERIOD_WIDTH),
        .JITTER_WIDTH(TX_JITTER_WIDTH),
        .lfsr_init(lfsr_init)
    ) clock_i(
        .clk(clk), 
        .rst(rst),
        .time_next(time_next),
        .period(period),
        .time_clock(time_clock),
        .cke_out(cke_out),
        .time_eq(time_eq)
    );
endmodule
