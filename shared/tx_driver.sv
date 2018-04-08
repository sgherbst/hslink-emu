`timescale 1ns/1ps

import filter_package::*;
import tx_package::*;

module tx_driver #(
    parameter setting=10
)(
    input in,
    input clk,
    output FILTER_IN_FORMAT out
);
    // verilog idiosyncracy, needed to initialize arrays to zero
    localparam signed [FILTER_IN_WIDTH-1:0] state_zero = 0;

    // store the filter state
    FILTER_IN_FORMAT state [N_TAPS] = '{(N_TAPS){state_zero}};

    // output assignment
    assign out = state[0];

    // create the taps
    TAP_FORMAT weight [N_TAPS];
    genvar k;
    generate
        for (k=0; k<N_TAPS; k=k+1) begin
            assign weight[k] = in ? TX_TAPS_PLUS[setting][k] : TX_TAPS_MINUS[setting][k];
            
            if ((k+1) < N_TAPS) begin 
                always @(posedge clk) begin
                    state[k] <= weight[k] + state[k+1];
                end
            end else begin
                always @(posedge clk) begin
                    state[k] <= weight[k];
                end
            end
        end
    endgenerate
endmodule
