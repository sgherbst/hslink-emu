`timescale 1ns/1ps

module clkgate (
    input wire en,
    input wire clk,
    output wire gated
);
    BUFHCE buf_i(.I(clk), .O(gated), .CE(en));
endmodule
