`timescale 1ns/1ps

import time_settings:time_t;

module time_manager #(
    parameter N=1,
    parameter time_bits=1
)(
    input time_t time_in [N],
    output time_t time_next,
    output time_t time_curr=0,
    input wire clk_sys
);
    generate
        if (N==1) begin
            assign time_next = time_in[0];
        end else if (N==2) begin
            assign time_next = (time_in[0] <= time_in[1]) ? time_in[0] : time_in[1];
        end else begin
            $error("Only N=1 and N=2 are supported at this time.");
        end
    endgenerate

    always @(posedge clk_sys) begin
        time_curr <= time_next;
    end
endmodule
