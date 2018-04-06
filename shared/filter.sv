`timescale 1ns/1ps

import signal_settings::*;
import time_settings::*;
import filter_settings::*;

module filter (
    input FILTER_IN_FORMAT in,
    input wire time_eq_in,
    output FILTER_OUT_FORMAT out,
    input wire clk_sys,
    input TIME_FORMAT time_next
);
    genvar k;

    // generate input history
    FILTER_IN_FORMAT value_hist [NUM_UI];
    DT_FORMAT time_hist [NUM_UI];
    
    reg time_eq_in_d = 1'b0;
    always @(posedge clk_sys) begin
        time_eq_in_d <= time_eq_in;
    end

    generate
        for (k=0; k<NUM_UI; k=k+1) begin : gen_input_hist
            if (k==0) begin
                assign value_hist[k] = in;
                mydff #(.N(DT_WIDTH)) time_dff_0(.in(time_next[DT_WIDTH-1:0]), .out(time_hist[0]), .cke(time_eq_in), .clk(clk_sys));
            end else begin
                mydff #(.N(FILTER_IN_WIDTH)) value_dff_k(.in(value_hist[k-1]), .out(value_hist[k]), .cke(time_eq_in_d), .clk(clk_sys));
                mydff #(.N(DT_WIDTH)) time_dff_k(.in(time_hist[k-1]), .out(time_hist[k]), .cke(time_eq_in), .clk(clk_sys));
            end
        end
    endgenerate
         
    // generate filter blocks, pulse responses, and products
    logic DT_FORMAT pwl_in [NUM_UI];
    logic signed [FILTER_STEP_WIDTH-1:0] steps [NUM_UI];
    logic signed [FILTER_PULSE_WIDTH-1:0] pulses [NUM_UI];
    logic signed [FILTER_PROD_WIDTH-1:0] prods [NUM_UI];

    generate
        for (k = 0; k < NUM_UI-1; k = k+1) begin : gen_pwl_blocks
            // PWL input time
            assign pwl_in[k] = time_next - time_hist[k]
            
            // PWL instantiation
            pwl #(.rom_name(FILTER_ROM_NAMES[k]),
                  .in_width(DT_WIDTH),
                  .in_point(DT_POINT),
                  .addr_width(FILTER_ADDR_WIDTHS[k]),
                  .addr_offset(FILTER_ADDR_OFFSETS[k]),
                  .segment_width(FILTER_SEGMENT_WIDTHS[k]),
                  .offset_width(FILTER_OFFSET_WIDTHS[k]),
                  .bias_val(FILTER_BIAS_VALS[k]),
                  .slope_width(FILTER_SLOPE_WIDTHS[k]),
                  .slope_point(FILTER_SLOPE_POINTS[k]),
                  .out_width(FILTER_STEP_WIDTH),
                  .out_point(FILTER_STEP_POINT)) pwl_k (.in(pwl_in[k]), .clk(clk_sys), .out(steps[k]));

            // Pulse responses
            if (k == 0) begin
                assign pulses[k] = steps[k];
            end else begin
                assign pulses[k] = steps[k] - steps[k-1];
            end

            // products
            mymult #(.a_bits(FILTER_PULSE_WIDTH)
                     .a_point(FILTER_PULSE_POINT),
                     .b_bits(FILTER_IN_WIDTH),
                     .b_point(FILTER_IN_POINT),
                     .c_bits(FILTER_PROD_WIDTH),
                     .c_point(FILTER_PROD_POINT)) prod_k (.a(pulses[k]),
                                                          .b(value_hist[k]),
                                                          .c(prods[k]));
        end
    endgenerate

    // sum all of the terms together
    mysum #(.in_bits(FILTER_PROD_WIDTH), .in_terms(NUM_UI), .out_bits(FILTER_OUT_WIDTH)) sum_i(.in(prods), .out(out));
endmodule
