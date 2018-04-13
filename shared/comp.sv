`timescale 1ns/1ps

import signal_package::*;

module comp (
    input FILTER_OUT_FORMAT in,
    input clk,
    input rst,
    output reg out
);
    always @(posedge clk) begin
        if (rst == 1'b1) begin
            out <= 1'b0;
        end else begin
            out <= (in >= $signed(0)) ? 1'b1 : 1'b0;
        end
    end
endmodule
