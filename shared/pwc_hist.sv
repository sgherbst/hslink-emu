`timescale 1ns/1ps

import signal_settings::*;
import time_settings::*;
import filter_settings::*;

module pwc_hist(
    input signal_t in,
    input wire time_eq_in,
    input wire clk_sys,
    input time_t time_next,
    output logic signed [VALUE_HIST_WIDTHS[0]-1:0] value_hist [NUM_UI],
    output logic [TIME_HIST_WIDTHS[0]-1:0] time_hist [NUM_UI],
);
    // delayed version of clock enable for values
    reg time_eq_in_d = 1'b0;
    always @(posedge clk_sys) begin
        time_eq_in_d <= time_eq_in;
    end

    // store input history
    genvar k, lsb, msb;

    generate
        // deal with first value point
        lsb = SIGNAL_POINT-VALUE_HIST_POINTS[0];
        msb = VALUE_HIST_WIDTHS[0] - 1 + lsb;
        if (((msb-lsb+1) != VALUE_HIST_WIDTHS[0]) || (lsb < 0)) begin
            $error("Problem generating first value history indices.");
        end
        assign value_hist[0] = in[msb:lsb];

        // deal with first time point
        lsb = TIME_POINT-TIME_HIST_POINTS[0];
        msb = TIME_HIST_WIDTHS[0] - 1 + lsb;
        if (((msb-lsb+1) != TIME_HIST_WIDTHS[0]) || (lsb < 0)) begin
            $error("Problem generating first time history indices.");
        end
        mydff #(.N(TIME_HIST_WIDTHS[0])) mod_time_hist_0(.in(msb:lsb]),
                                                         .out(time_hist[0][TIME_HIST_WIDTHS[0]-1:0]),
                                                         .clk(clk_sys),
                                                         .cke(time_eq_in));

        // deal with general time and value points
        for (k=1; k <= num_ui-1; k=k+1) begin : gen_hist_dffs
            // value point
            lsb = VALUE_HIST_POINTS[k-1]-VALUE_HIST_POINTS[k];
            msb = VALUE_HIST_WIDTHS[k] - 1 + lsb;
            if (((msb-lsb+1) != VALUE_HIST_WIDTHS[k])) || (lsb < 0)) begin
                $error("Problem generating value history.");
            end
            mydff #(.N(VALUE_HIST_WIDTHS[k])) mod_value_hist (.in(value_hist[k-1][msb:lsb]),
                                                              .out(value_hist[k][VALUE_HIST_WIDTHS[k]-1:0]),
                                                              .clk(clk_sys),
                                                              .cke(time_eq_in_d));

            // time point
            lsb = TIME_HIST_POINTS[k-1]-TIME_HIST_POINTS[k];
            msb = TIME_HIST_WIDTHS[k] - 1 + lsb;
            if (((msb-lsb+1) != TIME_HIST_WIDTHS[k]) || (lsb < 0)) begin
                $error("Problem generating time history.");
            end
            mydff #(.N(TIME_HIST_WIDTHS[k])) mod_time_hist (.in(time_hist[k-1][msb:lsb]),
                                                            .out(time_hist[k][TIME_HIST_WIDTHS[k]-1:0]),
                                                            .clk(clk_sys),
                                                            .cke(time_eq_in));
        end
    endgenerate

endmodule