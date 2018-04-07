`timescale 1ns/1ps

import filter_package::*;

module tx_driver (
    input in,
    input clk,
    output FILTER_IN_FORMAT out = 0
);
    localparam longint one = longint'(real'(1)*(real'(2)**real'(FILTER_IN_POINT)));
    localparam longint zero = longint'(real'(-1)*(real'(2)**real'(FILTER_IN_POINT)));

    FILTER_IN_FORMAT drv;
    assign drv = in ? one : zero;

    always @(posedge clk) begin
        out <= drv;
    end
endmodule
