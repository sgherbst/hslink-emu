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
    output wire clk_rx_n,
    output wire clk_dbg
);
    wire locked;
    
    clk_wiz_0 clk_wiz_0_i(
        // I/O for MMCM
        .reset(1'b0),
        .locked(locked),

        // input clock (differential)
        .clk_in1_p(SYSCLK_P),
        .clk_in1_n(SYSCLK_N),

        // ungated clock
        .clk_out1(clk_sys),

        // TX clock
        .clk_out2(   clk_tx),
        .clk_out2_ce(cke_tx),

        // RX clock (rising edge)
        .clk_out3(   clk_rx_p),
        .clk_out3_ce(cke_rx_p),

        // RX clock (falling edge)
        .clk_out4(   clk_rx_n),
        .clk_out4_ce(cke_rx_n)

        // Debug clock (for ILA/VIO)
        .clk_out5(clk_dbg)
     );
endmodule
