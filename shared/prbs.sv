`timescale 1ns/1ps

// reference: https://www.xilinx.com/support/documentation/application_notes/xapp210.pdf
module prbs #(
    parameter n=16,
    parameter init=2
)(
    input wire clk,
    input wire rst,
    output out
);
    wire [n-1:0] state;
    assign out = state[0];
    
    lfsr #(
        .n(n),
        .init(init)
    ) lfsr_i (
        .clk(clk),
        .cke(1'b1),
        .rst(rst),
        .state(state)
    );
endmodule
