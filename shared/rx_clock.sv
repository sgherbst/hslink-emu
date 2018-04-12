`timescale 1ns/1ps

import time_package::TIME_FORMAT;

module rx_clock #(
    parameter lfsr_init = 3
)(
    input wire clk,
    input wire rst,
    input TIME_FORMAT time_next,
    input wire [DCO_CODE_WIDTH-1:0] code,
    output TIME_FORMAT time_clock,
    output wire [1:0] cke_out,
    output wire time_eq
);
    // offset and slope
    wire [DCO_OFFSET_WIDTH-1:0] offset = DCO_OFFSET_VAL;
    wire [DCO_SLOPE_WIDTH-1:0] slope = DCO_SLOPE_VAL;

    // compute linear correction
    wire [DCO_PROD_WIDTH-1:0] prod;
    my_mult_unsigned #(
        .a_bits(DCO_SLOPE_WIDTH),
        .a_point(DCO_SLOPE_POINT),
        .b_bits(DCO_CODE_WIDTH),
        .b_point(DCO_CODE_POINT),
        .c_bits(DCO_PROD_WIDTH),
        .c_point(DCO_PROD_POINT)
    ) mult_i (
        .a(slope),
        .b(code),
        .c(prod)
    );

    // compute total period
    wire [DCO_PERIOD_WIDTH-1:0] period = offset - prod;

    // instantiate the clock
    clock #(
        .N(2),
        .PERIOD_WIDTH(DCO_PERIOD_WIDTH),
        .JITTER_WIDTH(RX_JITTER_WIDTH),
        .lfsr_init(lfsr_init)
    ) clock_i(.clk(clk), 
        .rst(rst),
        .time_next(time_next),
        .period(period),
        .time_clock(time_clock),
        .cke_out(cke_out),
        .time_eq(time_eq)
    );
endmodule
