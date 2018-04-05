`timescale 1ns/1ps

module mydff #(
    parameter N=1,
) (
    input wire [N-1:0] in,
    input wire clk,
    input wire cke,
    output reg [N-1:0] out = 0
);
    always @(posedge clk) begin
        if (cke == 1'b1) begin
            out <= in;
        end else begin
            out <= out;
        end
    end
endmodule
