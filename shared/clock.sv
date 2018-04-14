`timescale 1ns/1ps

import time_package::TIME_FORMAT;

module clock #(
    parameter integer N = 1,
    parameter integer PERIOD_WIDTH = 1,
    parameter integer JITTER_WIDTH = 1,
    parameter integer UPDATE_WIDTH = 1,
    parameter integer JITTER_LFSR_WIDTH = 1,
    parameter integer JITTER_SCALE_WIDTH = 1,
    parameter integer JITTER_SCALE_POINT = 1,
    parameter lfsr_init = 1
)(
    input wire clk,
    input wire rst,
    input TIME_FORMAT time_next,
    input wire [PERIOD_WIDTH-1:0] period,
    input wire [JITTER_SCALE_WIDTH-1:0] jitter_scale,
    output TIME_FORMAT time_clock,
    output reg [N-1:0] cke_out,
    output wire time_eq
);
    // clock gating signal
    assign time_eq = (time_next == time_clock) ? 1'b1 : 1'b0;

    // lfsr for jitter
    wire [JITTER_LFSR_WIDTH-1:0] jitter_lfsr_state;
    lfsr_cke #(
        .n(JITTER_LFSR_WIDTH),
        .init(lfsr_init)
    ) lfsr_i(
        .clk(clk),
        .cke(time_eq),
        .rst(rst),
        .state(jitter_lfsr_state)
    );

    // scale jitter by the desired amount
    wire signed [JITTER_WIDTH-1:0] jitter;
    my_mult_signed #(
        .a_bits(JITTER_LFSR_WIDTH),
        .a_point(0),

        // note that the signed version of
        // the scale factor requires an 
        // extra bit
        .b_bits(JITTER_SCALE_WIDTH+1), 

        .b_point(JITTER_SCALE_POINT),
        .c_bits(JITTER_WIDTH),
        .c_point(TIME_POINT)
    ) jitter_prod (
        .a($signed(jitter_lfsr_state)),
        .b($signed({1'b0, jitter_scale})),
        .c(jitter)
    );

    // compute the time increment, including jitter
    // it's signed although the top bit should never be set
    wire signed [UPDATE_WIDTH:0] time_update_signed;
    assign time_update_signed = $signed({1'b0, period}) + jitter;

    // trim off the sign bit to get the unsigned time update
    wire [UPDATE_WIDTH-1:0] time_update;
    assign time_update = time_update_signed[UPDATE_WIDTH-1:0];

    // update the clock time
    TIME_FORMAT time_clock_next;
    assign time_clock_next = time_clock + time_update;
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
