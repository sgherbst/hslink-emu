`timescale 1ns/1ps

module my_dff_cke #(
    parameter n=1,
    parameter init=0
) (
    input wire [n-1:0] d,
    output reg [n-1:0] q,
    input wire clk,
    input wire rst,
    input wire cke
);
    always @(posedge clk) begin
        if (rst == 1'b1) begin
            q <= init;
        end else if (cke == 1'b1) begin
            q <= d;
        end else begin
            q <= q;
        end
    end
endmodule
