`timescale 1ns/1ps

import signal_package::*;

module comp (
    input FILTER_OUT_FORMAT in,
    input clk,
    output reg out=1'b0
);
    always @(posedge clk) begin
        out <= (in >= $signed(0)) ? 1'b1 : 1'b0;
    end
endmodule
