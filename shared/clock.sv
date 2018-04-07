`timescale 1ns/1ps

import time_package::TIME_FORMAT;

module clock #(
    parameter integer N = 1,
    parameter integer TIME_INC_BITS = 1
)(
    input wire clk_orig,
    input wire clk_sys,
    input TIME_FORMAT time_next,
    input wire [TIME_INC_BITS-1:0] inc,
    output TIME_FORMAT time_clock=0,
    output wire [N-1:0] clk_out,
    output wire time_eq
);
    // clock gating signal
    assign time_eq = (time_next == time_clock) ? 1'b1 : 1'b0;

    // clock period progression logic
    always @(posedge clk_sys) begin
        if (time_eq == 1'b1) begin
            time_clock <= time_clock + inc;
        end else begin
            time_clock <= time_clock;
        end
    end

    // clock gating logic
    wire [N-1:0] clk_en;

    // treat one- and two- phase differently
    generate
        if (N==1) begin : one_phase
            assign clk_en = time_eq;
        end else if (N==2) begin : two_phase
            reg mask = 0;
            always @(posedge clk_sys) begin
                if (time_eq == 1'b1) begin
                    mask <= ~mask;
                end else begin
                    mask <= mask;
                end
            end
            assign clk_en[0] = time_eq & mask;
            assign clk_en[1] = time_eq & (~mask);
        end else begin : illegal_phase
            $error("Only N=1 and N=2 are supported at this time.");
        end
    endgenerate

    // delay clock enable by one cycle
    reg [N-1:0] clk_en_d = 0;
    always @(posedge clk_sys) begin
        clk_en_d <= clk_en;
    end

    // clock gate instantiation
    genvar k;
    generate
        for (k=0; k<N; k=k+1) begin : clk_gate_gen
            clkgate gate_i(.en(clk_en_d[k]), .clk(clk_orig), .gated(clk_out[k]));
        end
    endgenerate
endmodule
