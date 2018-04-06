`timescale 1ns/1ps

module pwl #(
    parameter rom_name = "rom.mem",
    parameter in_width = 1,
    parameter in_point = 1,
    parameter addr_width = 1,
    parameter addr_offset = 1,
    parameter segment_width = 1,
    parameter offset_width = 1,
    parameter bias_val = 1,
    parameter slope_width = 1,
    parameter slope_point = 1,
    parameter out_width = 1,
    parameter out_point = 1
)(
    input [in_width-1:0] in,
    output signed [out_width-1:0] out,
    input clk
);
    // local parameters defined for convenience
    localparam rom_data_width = offset_width+slope_width;
    localparam in_diff_width = segment_width+addr_width;
    localparam prod_width = segment_width + slope_width + 1; // extra bit added to account for making segment signed
    
    // instantiate the rom
    wire [addr_width-1:0] rom_addr;
    wire [rom_data_width-1:0] rom_data;
    myrom #(.addr_bits(addr_width),
            .data_bits(rom_data_width),
            .filename(rom_name)) myrom_i(.addr(rom_addr), .dout(rom_data), .clk(clk));

    // calculate rom addr
    wire [in_diff_width-1:0] in_diff = in - addr_offset;
    assign rom_addr = in_diff[in_diff_width-1:segment_width];

    // calculate length along segment
    // it is stored with a latency of one clock cycle
    // to match the rom latency
    reg [segment_width-1:0] segment = 1'b0;
    always @(posedge clk) begin
        segment <= in_diff[segment_width-1:0];
    end

    // interpretation of memory contents as signed offset and slope
    wire signed [offset_width-1:0] offset = $signed(rom_data[offset_width+slope_width-1:slope_width]);
    wire signed [slope_width-1:0] slope = $signed(rom_data[slope_width-1:0]);

    // compute linear correction
    wire signed [prod_width-1:0] prod;
    mymult #(.a_bits(segment_width+1), // add one to segment width to account for conversion to signed number
             .a_point(in_point),
             .b_bits(slope_width),
             .b_point(slope_point),
             .c_bits(prod_width),
             .c_point(out_point)) my_mult_i (.a($signed({1'b0, segment})),
                                             .b(slope),
                                             .c(prod));
  
    // assign output as sum of linear correction, offset from ROM, and a bias value
    assign out = offset + prod + bias_val;
endmodule
