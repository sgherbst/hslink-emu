`timescale 1ns/1ps

import signal_settings::*;
import time_settings::*;
import filter_settings::*;

module filter (
    input signal_t in,
    input wire time_eq_in,
    output signal_t out,
    input wire clk_sys,
    input time_t time_next
);
    // generate input history
    logic signed [VALUE_HIST_WIDTHS[0]-1:0] value_hist [NUM_UI],
    logic [TIME_HIST_WIDTHS[0]-1:0] time_hist [NUM_UI],
    pwc_hist pwc_hist_i(.in(in), .time_eq_in(time_eq_in), .clk_sys(clk_sys), .time_next(time_next),
                        .value_hist(value_hist), .time_hist(time_hist));

    // generate filter blocks, pulse responses, and products
    logic signed [MAX_PWL_OUT_WIDTH-1:0] pwl_out [NUM_UI];
    logic signed [MAX_PULSE_WIDTH-1:0] pulses [NUM_UI];
    logic signed [PRODUCT_WIDTH-1:0] prods [NUM_UI];

    genvar k, lshift;
    generate
        for (k = 0; k < NUM_UI-1; k = k+1) begin : gen_filter_blocks
            // filter block
            filter_block #(.n(k)) filter_block_i(.time_point(time_hist[k][TIME_HIST_WIDTHS[k]-1:0]),
                                                 .time_next(time_next),
                                                 .pwl_out(pwl_out[k][PWL_OUT_WIDTHS[k]-1:0]),
                                                 .clk_sys(clk_sys));

            // pulse responses
            if (k == 0) begin
                assign pulses[PULSE_WIDTHS[0]-1:0] = pwl_out[0][PULSE_WIDTHS[0]-1:0] + PULSE_OFFSET_VALS[k];
            end else begin
                // plus term: from older time
                lshift = PULSE_OFFSET_POINTS[k] - PWL_OFFSET_POINTS[k];
                if (lshift < 0) begin
                    $error("Problem forming pulse response: pulse_term_p.");
                end
                wire [PULSE_TERM_WIDTHS[k]-1:0] pulse_term_p = pwl_out[k][PWL_OUT_WIDTHS[k]-1:0] <<< lshift;

                // minus term: from newer time
                lshift = PULSE_OFFSET_POINTS[k] - PWL_OFFSET_POINTS[k-1];
                if (lshift < 0) begin
                    $error("Problem forming pulse response: pulse_term_m.");
                end
                wire [PULSE_TERM_WIDTHS[k]-1:0] pulse_term_m = pwl_out[k-1][PWL_OUT_WIDTHS[k-1]-1:0] <<< lshift

                // add pulse offset to form the complete pulse term
                assign pulses[k] = pulse_term_p - pulse_term_m + PULSE_OFFSET_VALS[k];
            end

            // products
            mymult #(.a_bits(PULSE_WIDTHS[k]),
                     .a_point(PULSE_OFFSET_POINTS[k]),
                     .b_bits(VALUE_HIST_WIDTHS[k]),
                     .b_point(VALUE_HIST_POINTS[k]),
                     .c_bits(PRODUCT_WIDTH),
                     .c_point(OUT_POINT)) prod_mult_i (.a(pulses[k][PULSE_WIDTHS[k]-1:0]),
                                                       .b(value_hist[k][VALUE_HIST_WIDTHS[k]-1:0]),
                                                       .c(prods[k]));
        end
    endgenerate

    // sum all of the terms together
    mysum #(.in_bits(PRODUCT_WIDTH), .in_terms(NUM_UI), .out_bits(SIGNAL_WIDTH)) sum_i(.in(prods), .out(out));
endmodule
