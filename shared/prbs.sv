`timescale 1ns/1ps

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
        .rst(rst),
        .state(state)
    );
endmodule
