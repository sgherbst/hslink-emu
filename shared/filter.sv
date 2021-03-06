`timescale 1ns/1ps

import signal_package::*;
import time_package::*;
import filter_package::*;

module filter (
    input clk,
    input rst,
    input FILTER_IN_FORMAT in,
    input wire time_eq_in,
    output FILTER_OUT_FORMAT out,
    input TIME_FORMAT time_next,
    input [RX_SETTING_WIDTH-1:0] rx_setting
);
    // input history
    FILTER_IN_FORMAT value_hist [NUM_UI];
    FILTER_IN_FORMAT value_hist_reg [1:NUM_UI-1];
    DT_FORMAT time_hist [NUM_UI];
    
    // generate delayed version of clock enable
    wire time_eq_in_d;
    my_dff dff_time_eq (
        .d(time_eq_in),
        .q(time_eq_in_d),
        .clk(clk),
        .rst(rst)
    );
    
    genvar k;
    generate
        for (k=0; k<NUM_UI; k=k+1) begin : gen_input_hist
            if (k==0) begin
                // value
                assign value_hist[k] = in;

                // time
                my_dff_cke #(
                    .n(DT_WIDTH)
                ) time_dff_0(
                    .d(time_next[DT_WIDTH-1:0]),
                    .q(time_hist[0]),
                    .cke(time_eq_in),
                    .clk(clk),
                    .rst(rst)
                );
            end else begin
                // value
                assign value_hist[k] = value_hist_reg[k];

                my_dff_cke #(
                    .n(FILTER_IN_WIDTH)
                ) value_dff_k(
                    .d(value_hist[k-1]),
                    .q(value_hist_reg[k]),
                    .cke(time_eq_in_d), 
                    .clk(clk),
                    .rst(rst)
                );

                // time
                my_dff_cke #(
                    .n(DT_WIDTH)
                ) time_dff_k (
                    .d(time_hist[k-1]),
                    .q(time_hist[k]),
                    .cke(time_eq_in),
                    .clk(clk),
                    .rst(rst)
                );
            end
        end
    endgenerate
         
    // generate pwl tables, pulse responses, and products
    DT_FORMAT pwl_in [NUM_UI];
    FILTER_STEP_FORMAT steps [NUM_UI];
    FILTER_PULSE_FORMAT pulses [NUM_UI];
    FILTER_PROD_FORMAT prods [NUM_UI];

    // note that genvar k is reused from above...
    generate
        for (k=0; k<NUM_UI; k=k+1) begin : gen_pwl_blocks
            // PWL input time
            assign pwl_in[k] = time_next - time_hist[k];
            
            // PWL instantiation
            pwl #(
                .segment_rom_name(FILTER_SEGMENT_ROM_NAMES[k]),
                .bias_rom_name(FILTER_BIAS_ROM_NAMES[k]),
                .bias_width(FILTER_BIAS_WIDTHS[k]),
                .setting_width(RX_SETTING_WIDTH),
                .in_width(DT_WIDTH),
                .in_point(DT_POINT),
                .addr_width(FILTER_ADDR_WIDTHS[k]),
                .addr_offset(FILTER_ADDR_OFFSETS[k]),
                .segment_width(FILTER_SEGMENT_WIDTHS[k]),
                .offset_width(FILTER_OFFSET_WIDTHS[k]),
                .slope_width(FILTER_SLOPE_WIDTHS[k]),
                .slope_point(FILTER_SLOPE_POINTS[k]),
                .out_width(FILTER_STEP_WIDTH),
                .out_point(FILTER_STEP_POINT)
            ) pwl_k (
                .in(pwl_in[k]), 
                .out(steps[k]),
                .setting(rx_setting),
                .clk(clk),
                .rst(rst)
            );

            // Pulse responses
            if (k == 0) begin
                assign pulses[k] = steps[k];
            end else begin
                assign pulses[k] = steps[k] - steps[k-1];
            end

            // products
            my_mult_signed #(
                .a_bits(FILTER_PULSE_WIDTH),
                .a_point(FILTER_PULSE_POINT),
                .b_bits(FILTER_IN_WIDTH),
                .b_point(FILTER_IN_POINT),
                .c_bits(FILTER_PROD_WIDTH),
                .c_point(FILTER_PROD_POINT)
            ) prod_k (
                .a(pulses[k]),
                .b(value_hist[k]),
                .c(prods[k])
            );
        end
    endgenerate

    // sum all of the terms together
    my_sum #(
        .in_bits(FILTER_PROD_WIDTH), 
        .in_terms(NUM_UI), 
        .out_bits(FILTER_OUT_WIDTH)
    ) sum_i (
        .in(prods), 
        .out(out)
    );
endmodule
