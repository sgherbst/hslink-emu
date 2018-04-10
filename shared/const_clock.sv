`timescale 1ns/1ps

import time_package::TIME_FORMAT;

module const_clock #(
    parameter integer N = 1,
    parameter longint INC = 1
)(
    input wire clk,
    input wire rst,
    input TIME_FORMAT time_next,
    output TIME_FORMAT time_clock,
    output wire [N-1:0] cke_out,
    output wire time_eq
);
    // calculate time increment representation
    localparam TIME_INC_BITS = $clog2(1+INC);

    // represent delta time
    wire [TIME_INC_BITS-1:0] inc = INC;

    // instantiate the clock
    clock #(.N(N), .TIME_INC_BITS(TIME_INC_BITS)) clock_i(.clk(clk), 
                                                          .rst(rst),
                                                          .time_next(time_next),
                                                          .inc(inc),
                                                          .time_clock(time_clock),
                                                          .cke_out(cke_out),
                                                          .time_eq(time_eq));
endmodule
