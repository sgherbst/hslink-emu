`timescale 1ns/1ps

module pwl #(
    parameter pwl_addr_bits=1,
    parameter pwl_data_bits=1,
    parameter pwl_low_bits=1,
    parameter table_addr_bits=1,
    parameter offset_bits=1,
    parameter slope_bits=1,
    parameter slope_res_bits=1,
    parameter t_res_bits=1,
    parameter v_res_bits=1
)(
    input [pwl_addr_bits-1:0] t,
    output [pwl_data_bits-1:0] v,
    output [table_addr_bits-1:0] addr_to_rom,
    input [offset_bits+slope_bits-1:0] data_from_rom,
    input clk
);
    localparam prod_width = slope_bits+pwl_low_bits+1; // extra bit to account for unsigned-to-signed conversion of low_addr_bits
    localparam shift_amount = slope_res_bits + t_res_bits - v_res_bits;
    localparam shift_width = prod_width - shift_amount;

    wire [table_addr_bits-1:0] mid_addr_bits = t[table_addr_bits+pwl_low_bits-1:pwl_low_bits];
    wire [pwl_low_bits-1:0] low_addr_bits = t[pwl_low_bits-1:0];

    // add logic to deal with out-of-range address if necessary
    generate
        if (pwl_addr_bits > (table_addr_bits+pwl_low_bits)) begin
            wire [pwl_addr_bits-table_addr_bits-pwl_low_bits-1:0] top_addr_bits = t[pwl_addr_bits-1:table_addr_bits+pwl_low_bits];
            wire out_of_range = |top_addr_bits;
            assign addr_to_rom = (out_of_range == 1'b1) ? {table_addr_bits{1'b1}}: t[table_addr_bits+pwl_low_bits-1:pwl_low_bits];
        end else if (pwl_addr_bits == (table_addr_bits+pwl_low_bits)) begin
            assign addr_to_rom = t[pwl_addr_bits-1:pwl_low_bits];
        end else begin
            assign addr_to_rom = {{(table_addr_bits-(pwl_addr_bits-pwl_low_bits)){1'b0}}, t[pwl_addr_bits-1:pwl_low_bits]};
        end
    endgenerate

    // interpretation of memory contents as signed offset and slope
    wire signed [offset_bits-1:0] offset = $signed(data_from_rom[offset_bits+slope_bits-1:slope_bits]);
    wire signed [slope_bits-1:0] slope = $signed(data_from_rom[slope_bits-1:0]);

    // delay low_addr_bits to match latency of synchronous ROM
    reg [pwl_low_bits-1:0] low_addr_bits_d;
    always @(posedge clk) begin
        low_addr_bits_d <= low_addr_bits;
    end

    // compute linear correction
    wire signed [prod_width-1:0] prod = slope * $signed({1'b0, low_addr_bits_d}); 
    wire signed [shift_width-1:0] shift = prod >>> shift_amount;
    
    // assign output as sum of linear correction and offset
    assign v = offset+shift;
endmodule

