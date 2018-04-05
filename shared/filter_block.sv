`timescale 1ns/1ps

import signal_settings::*;
import time_settings::*;
import filter_settings::*;

module pwl #(
    parameter n = 1
)(
    logic [TIME_HIST_WIDTHS[k]-1:0] time_point,
    logic [TIME_BITS-1:0] time_next,
    logic [PWL_OUT_WIDTHS[k]-1:0] pwl_out,
    logic clk_sys
);
    localparam DT_POINT = PWL_ADDR_POINTS[k];
    localparam DT_WIDTH = TIME_HIST_POINTS[k] - DT_POINT;
    localparam lsb_slope = 0;
    localparam msb_slope = PWL_SLOPE_WIDTHS[k] - 1 + lsb_slope;
    localparam lsb_offset = msb_slope + 1;
    localparam msb_offset = PWL_OFFSET_WIDTHS[k] - 1 + lsb_offset;

    logic [PWL_ADDR_WIDTHS[k]-1:0] rom_addr;
    logic [PWL_OFFSET_WIDTHS[k]+PWL_SLOPE_WIDTHS[k]-1:0] rom_data;

    logic signed [PWL_OFFSET_WIDTHS[k]-1:0] offset = rom_data[msb_offset:lsb_offset];
    logic signed [PWL_SLOPE_WIDTHS[k]-1:0] slope = rom_data[msb_slope:lsb_slope];

    // delay dt by one clock cycle so its latency matches that of ROM
    logic signed [DT_WIDTH-1:0] dt;
    logic signed [DT_WIDTH-1:0] dt_d;
    always @(posedge clk_sys) begin
        dt_d <= dt;
    end

    logic signed [PWL_LIN_CORR_WIDTHS[k]-1:0] lin_corr;
    mymult #(.a_bits(PWL_SLOPE_WIDTHS[k]),
             .a_point(PWL_SLOPE_POINTS[k]),
             .b_bits(DT_WIDTH),
             .b_point(DT_POINT),
             .c_bits(PWL_LIN_CORR_WIDTHS[k])
             .c_point(PWL_OFFSET_POINTS[k])) prod_mult_i (.a(slope), .b(dt_d), .c(lin_corr));

    assign pwl_out = lin_corr_d + offset;

    // ROM interface
    genvar lsb, msb;
    generate
        // generate the time increment used for linear correction
        lsb = 0;
        msb = DT_WIDTH - 1 + lsb;
        if (((msb-lsb+1) != DT_WIDTH) || (lsb < 0) || (msb > TIME_HIST_WIDTHS[k])) begin
            $error("Problem generating ROM interface (linear correction).");
        end
        assign dt = time_point[msb:lsb];

        // generate the ROM address
        lsb = DT_WIDTH;
        msb = PWL_ADDR_WIDTHS[k] - 1 + lsb;
        if (((msb-lsb+1) != PWL_ADDR_WIDTHS[k]) || (lsb < 0) || (msb > TIME_HIST_WIDTHS[k])) begin
            $error("Problem generating ROM interface (address).");
        end
        assign rom_addr = time_point[PWL_ADDR_WIDTHS[k]-1+DT_WIDTH:DT_WIDTH];
    endgenerate

    // ROM instantiation
    myrom #(.addr_bits(PWL_ADDR_WIDTHS[k]),
            .data_bits(PWL_OFFSET_WIDTHS[k]+PWL_SLOPE_WIDTHS[k]),
            .filename(PWL_ROM_NAMES[k])) myrom_i (.addr(rom_addr), .dout(rom_data), .clk(clk_sys));
endmodule

