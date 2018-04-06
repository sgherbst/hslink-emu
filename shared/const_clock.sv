`timescale 1ns/1ps

import time_settings::time_t;

module const_clock #(
    parameter integer N = 1,
    parameter longint INC = 1
)(
    input wire clk_orig,
    input wire clk_sys,
    input time_t time_next,
    output time_t time_clock,
    output wire [N-1:0] clk_out,
    output wire time_eq
);

    // calculate time increment representation
    localparam TIME_INC_BITS = $clog2(1+inc);

    // represent delta time
    wire [TIME_INC_BITS-1:0] inc = INC;

    // instantiate the clock
    clock #(.N(N), .TIME_INC_BITS(TIME_INC_BITS)) clock_i(.clk_orig(clk_orig), .clk_sys(clk_sys), .time_next(time_next), .inc(inc), .time_clock(time_clock), .clk_out(clk_out), .time_eq(time_eq));

endmodule
