`timescale 1ns/1ps

module clkgen(
    input wire SYSCLK_P,
    input wire SYSCLK_N,
    input wire cke_tx,
    input wire cke_rx_p,
    input wire cke_rx_n,
    output wire clk_sys,
    output wire clk_tx,
    output wire clk_rx_p,
    output wire clk_rx_n
);
    reg clk_orig = 1'b0;
    initial begin
        forever begin
            clk_orig=1'b0;
            #50;
            clk_orig=1'b1;
            #50;
        end
    end

    clkgate clkgate_sys (.en(1'b1),     .gated(clk_sys),  .clk(clk_orig));
    clkgate clkgate_tx  (.en(cke_tx),   .gated(clk_tx),   .clk(clk_orig));
    clkgate clkgate_rx_p(.en(cke_rx_p), .gated(clk_rx_p), .clk(clk_orig));
    clkgate clkgate_rx_n(.en(cke_rx_n), .gated(clk_rx_n), .clk(clk_orig));

endmodule
