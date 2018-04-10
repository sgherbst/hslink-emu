`timescale 1ns/1ps

import time_package::*;

module adc #(
    parameter name = "adc",
    parameter ext = ".txt",
    parameter sig_bits = 1,
    parameter sig_point = 1
)(
    input wire clk,
    input wire rst,
    input TIME_FORMAT time_curr,
    input wire signed [sig_bits-1:0] sig
);
    (* mark_debug = "true" *) TIME_FORMAT time_samp;
    (* mark_debug = "true" *) reg [sig_bits-1:0] sig_samp;
endmodule
