`timescale 1ns/1ps

module clkgen(
    input wire SYSCLK_P,
    input wire SYSCLK_N,
    output wire clk_orig
);

    wire locked;
    clk_wiz_0 clk_wiz_0_i(.clk_out1(clk_orig), .reset(1'b0), .locked(locked), .clk_in1_p(SYSCLK_P), .clk_in1_n(SYSCLK_N)); 

endmodule
