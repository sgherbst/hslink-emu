`timescale 1ns/1ps

import time_package::TIME_FORMAT;

module clock #(
    parameter integer N = 1,
    parameter integer PERIOD_WIDTH = 1,
    parameter integer JITTER_WIDTH = 1,
    parameter lfsr_init = 1
)(
    input wire clk,
    input wire rst,
    input TIME_FORMAT time_next,
    input wire [PERIOD_WIDTH-1:0] period,
    output TIME_FORMAT time_clock,
    output reg [N-1:0] cke_out,
    output wire time_eq
);
    // clock gating signal
    assign time_eq = (time_next == time_clock) ? 1'b1 : 1'b0;

    // lfsr for jitter
    wire [JITTER_WIDTH-1:0] jitter;
    lfsr_cke #(
        .n(JITTER_WIDTH),
        .init(lfsr_init)
    ) lfsr_i(
        .clk(clk),
        .cke(time_eq),
        .rst(rst),
        .state(jitter)
    );

    // clock period progression logic
    TIME_FORMAT time_clock_next;
    assign time_clock_next = time_clock + period + jitter;
    my_dff_cke #(
        .n(TIME_WIDTH)
    ) time_prog_dff (
        .d(time_clock_next),
        .q(time_clock),
        .clk(clk),
        .rst(rst),
        .cke(time_eq)
    );

    // clock gating logic
    wire [N-1:0] clk_en;

    // treat one- and two- phase differently
    generate
        if (N==1) begin : one_phase
            assign clk_en = time_eq;
        end else if (N==2) begin : two_phase
            // flip mask back and forth
            wire mask;
            my_dff_cke mask_dff (
                .d(~mask),
                .q(mask),
                .clk(clk),
                .rst(rst),
                .cke(time_eq)
            );

            assign clk_en[0] = time_eq & mask;
            assign clk_en[1] = time_eq & (~mask);
        end else begin : illegal_phase
            $error("Only N=1 and N=2 are supported at this time.");
        end
    endgenerate

    // delay clock enable by one cycle
    my_dff #(
        .n(N)
    ) cke_dff (
        .d(clk_en),
        .q(cke_out),
        .clk(clk),
        .rst(rst)
    );
endmodule
