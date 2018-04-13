`timescale 1ns/1ps

import lfsr_package::*;

// reference: https://www.xilinx.com/support/documentation/application_notes/xapp210.pdf
module lfsr_cke #(
    parameter n=16,
    parameter init=2
)(
    input wire clk,
    input wire rst,
    input wire cke,
    output wire [n-1:0] state
);
    // make sure that output width is valid
    generate
        if (LFSR_N_TAPS[n] == -1) begin
            $error("Invalid output width.");
        end
    endgenerate

    // generate the least significant bit
    reg lsb;
    always_comb begin
        lsb = 1'b0;
        for (int k=0; k<LFSR_N_TAPS[n]; k=k+1) begin
            lsb = lsb ^ state[LFSR_TAPS[n][k]-1];
        end
    end

    // generate the output state
    my_dff_cke #(
        .n(n),
        .init(init)
    ) state_update (
        .d({state[n-2:0], ~lsb}),
        .q(state),
        .clk(clk),
        .rst(rst),
        .cke(cke)
    );
endmodule
