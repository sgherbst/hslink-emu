`timescale 1ns/1ps

module lfsr #(
    parameter n=16,
    parameter init=2
)(
    input wire clk,
    input wire rst,
    output wire [n-1:0] state
);

    lfsr_cke #(
        .n(n),
        .init(init)
    ) lfsr_cke_i (
        .clk(clk),
        .rst(rst),
        .state(state),
        .cke(1'b1)
    );

endmodule
