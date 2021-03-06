`timescale 1ns/1ps

module my_mult_unsigned #(
    parameter a_bits=1,
    parameter a_point=1,
    parameter b_bits=1,
    parameter b_point=1,
    parameter c_bits=1,
    parameter c_point=1
) (
    input wire [a_bits-1:0] a,
    input wire [b_bits-1:0] b,
    output wire [c_bits-1:0] c
);
    localparam prod_width = a_bits + b_bits;
    localparam rshift = a_point + b_point - c_point;    

    wire [prod_width-1:0] prod = a*b;

    generate
        if (rshift >= 0) begin
            assign c = prod >>> rshift;
        end else begin
            assign c = prod <<< -rshift;
        end
    endgenerate
endmodule
