`timescale 1ns/1ps

import filter_package::*;

module tx_driver (
    input in,
    input clk,
    output FILTER_IN_FORMAT out
);
    localparam longint one = longint'(real'(1)*(real'(2)**real'(FILTER_IN_POINT)));
    localparam longint zero = longint'(real'(-1)*(real'(2)**real'(FILTER_IN_POINT)));

    assign out = in ? one : zero;
endmodule
