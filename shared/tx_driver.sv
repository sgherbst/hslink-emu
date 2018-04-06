`timescale 1ns/1ps

module tx_driver #(
    parameter width = 1,
    parameter point = 1
)(
    input in,
    input clk,
    output signed [width-1:0] out
);
    localparam longint one = longint'(real'(1)*(real'(2)**real'(point)));
    localparam longint zero = longint'(real'(-1)*(real'(2)**real'(point)));

    assign out = in ? one : zero;
endmodule
