`timescale 1ns/1ps

import filter_package::*;
import path_package::*;

module pwl #(
    // rom file name containing offsets and slopes,
    // but not bias values for each setting; those
    // are contained in another, smaller ROM
    parameter segment_rom_name = "rom.mem",

    // number of settings contained represented
    parameter setting_width = 1,

    // input formatting      
    parameter in_width = 1,
    parameter in_point = 1,

    // number of high bits taken from the
    // input to form the ROM address
    parameter addr_width = 1,

    // offset subtracted from input to
    // bias the start of the PWL table
    parameter addr_offset = 1,     

    // width of segment, i.e. the remaining 
    // low bits after the high bits have
    // been removed to address into the rom
    parameter segment_width = 1,

    // bias formatting
    // its point is taken to be out_point
    parameter bias_width = 1,

    // offset formatting
    // its point is taken to be out_point
    parameter offset_width = 1,

    // slope formatting
    parameter slope_width = 1,
    parameter slope_point = 1,

    // output formatting
    parameter out_width = 1,
    parameter out_point = 1,

    //////////////////////////////////////
    // needed only for multiple settings
    parameter bias_rom_name = "rom.mem", 
    //////////////////////////////////////
        
    //////////////////////////////////////
    // needed only for single setting
    parameter longint bias_val = 1
    //////////////////////////////////////
)(
    input [in_width-1:0] in,
    output signed [out_width-1:0] out,
    input clk,
    input rst,

    // only used if setting_width > 0
    input [setting_width-1:0] setting
);
    // local parameters defined for convenience
    localparam segment_rom_addr_width = setting_width+addr_width;
    localparam segment_rom_data_width = offset_width+slope_width;
    localparam in_diff_width = segment_width+addr_width;
    localparam prod_width = segment_width + slope_width + 1; // extra bit added to account for making segment signed
    
    //////////////////////////////////////
    // Segment ROM
    //////////////////////////////////////

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

    // interpretation of memory contents as signed offset, slope, and bias
    wire signed [offset_width-1:0] offset = $signed(segment_rom_data[offset_width+slope_width-1:slope_width]);
    wire signed [slope_width-1:0] slope = $signed(segment_rom_data[slope_width-1:0]);

    //////////////////////////////////////
    // Handling of one setting vs. multiple settings
    //////////////////////////////////////

    // Subtract address offset from input
    wire [in_diff_width-1:0] in_diff = in - addr_offset;

    wire signed [bias_width-1:0] bias;
    generate
        if (setting_width == 0) begin
            // setting input is unused
            assign segment_rom_addr = in_diff[in_diff_width-1:segment_width];

            // bias is a parameter, so it is just assigned
            // to the bias wire
            assign bias = bias_val;
        end else if (setting_width > 0) begin
            // setting input is used
            assign segment_rom_addr = {setting, in_diff[in_diff_width-1:segment_width]};

            // bias is variable, read from ROM 
            // depending on setting
            wire [bias_width-1:0] bias_rom_data;
            assign bias = $signed(bias_rom_data);
        
            // instantiate bias rom
            my_rom_sync #(
                .addr_bits(setting_width),
                .data_bits(bias_width),
                .filename({ROM_DIR, "/", bias_rom_name})
            ) bias_rom_i(
                .addr(setting),
                .dout(bias_rom_data),
                .clk(clk)
            );
        end else begin
            $error("Invalid setting width.");
        end
    endgenerate

    // calculate length along segment
    // it is stored with a latency of one clock cycle
    // to match the rom latency
    wire [segment_width-1:0] segment;
    my_dff #(
        .n(segment_width)
    ) my_dff_i (
        .d(in_diff[segment_width-1:0]),
        .q(segment),
        .clk(clk),
        .rst(rst)
    );

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
