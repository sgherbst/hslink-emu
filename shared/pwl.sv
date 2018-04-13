`timescale 1ns/1ps

import filter_package::*;
import path_package::*;

module pwl #(
    parameter segment_rom_name = "rom.mem",
    parameter bias_rom_name = "rom.mem",
    parameter bias_width = 1,
    parameter n_settings = 1,
    parameter setting_width = 1,   
    parameter in_width = 1,
    parameter in_point = 1,
    parameter addr_width = 1,
    parameter addr_offset = 1,
    parameter segment_width = 1,
    parameter offset_width = 1,
    parameter slope_width = 1,
    parameter slope_point = 1,
    parameter out_width = 1,
    parameter out_point = 1
)(
    input [in_width-1:0] in,
    output signed [out_width-1:0] out,
    input [setting_width-1:0] setting,
    input clk,
    input rst
);
    // local parameters defined for convenience
    localparam segment_rom_addr_width = setting_width+addr_width;
    localparam segment_rom_data_width = offset_width+slope_width;
    localparam in_diff_width = segment_width+addr_width;
    localparam prod_width = segment_width + slope_width + 1; // extra bit added to account for making segment signed
    
    // instantiate the segment rom
    wire [segment_rom_addr_width-1:0] segment_rom_addr;
    wire [segment_rom_data_width-1:0] segment_rom_data;

    my_rom_sync #(
        .addr_bits(segment_rom_addr_width),
        .data_bits(segment_rom_data_width),
        .filename({ROM_DIR, "/", segment_rom_name})
    ) segment_rom_i(
        .addr(segment_rom_addr),
        .dout(segment_rom_data),
        .clk(clk)
    );

    // instantiate the bias rom
    wire [bias_width-1:0] bias_rom_data;

    my_rom_sync #(
        .addr_bits(setting_width),
        .data_bits(bias_width),
        .filename({ROM_DIR, "/", bias_rom_name})
    ) bias_rom_i(
        .addr(setting),
        .dout(bias_rom_data),
        .clk(clk)
    );

    // calculate rom addr
    wire [in_diff_width-1:0] in_diff = in - addr_offset;
    assign segment_rom_addr = {setting, in_diff[in_diff_width-1:segment_width]};

    // calculate length along segment
    // it is stored with a latency of one clock cycle
    // to match the rom latency
    reg [segment_width-1:0] segment;
    always @(posedge clk) begin
        if (rst == 1'b1) begin
            segment <= 0;
        end else begin
            segment <= in_diff[segment_width-1:0];
        end
    end

    // interpretation of memory contents as signed offset, slope, and bias
    wire signed [offset_width-1:0] offset = $signed(segment_rom_data[offset_width+slope_width-1:slope_width]);
    wire signed [slope_width-1:0] slope = $signed(segment_rom_data[slope_width-1:0]);
    wire signed [bias_width-1:0] bias = $signed(bias_rom_data);

    // compute linear correction
    wire signed [prod_width-1:0] prod;
    my_mult_signed #(
        .a_bits(segment_width+1), // add one to segment width to account for conversion to signed number
        .a_point(in_point),
        .b_bits(slope_width),
        .b_point(slope_point),
        .c_bits(prod_width),
        .c_point(out_point)
    ) my_mult_i (
        .a($signed({1'b0, segment})),
        .b(slope),
        .c(prod)
    );
  
    // assign output as sum of linear correction, offset from ROM, and a bias value
    assign out = offset + prod + bias;
endmodule
