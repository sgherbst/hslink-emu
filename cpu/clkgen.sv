`timescale 1ns/1ps

module clkgen(
    input wire SYSCLK_P,
    input wire SYSCLK_N,
    output reg clk_orig=1'b0
);

    initial begin
        forever begin
            clk_orig=1'b0;
            #50;
            clk_orig=1'b1;
            #50;
        end
    end

endmodule
