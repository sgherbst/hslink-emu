`timescale 1ns/1ps

module my_dff #(
    parameter n=1,
    parameter init=0
) (
    input wire [n-1:0] d,
    output reg [n-1:0] q,
    input wire clk,
    input wire rst
);
    my_dff_cke #(
        .n(n),
        .init(init)
    ) my_dff_cke_i (
        .d(d),
        .q(q),
        .clk(clk),
        .rst(rst),
        .cke(1'b1)
    );
endmodule
