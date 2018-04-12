`timescale 1ns/1ps

module my_mult_signed #(
    parameter a_bits=1,
    parameter a_point=1,
    parameter b_bits=1,
    parameter b_point=1,
    parameter c_bits=1,
    parameter c_point=1
) (
    input wire signed [a_bits-1:0] a,
    input wire signed [b_bits-1:0] b,
    output wire signed [c_bits-1:0] c
);
    localparam prod_width = a_bits + b_bits;
    localparam rshift = a_point + b_point - c_point;    

    wire signed [prod_width-1:0] prod = a*b;

    generate
        if (rshift >= 0) begin
            assign c = prod >>> rshift;
        end else begin
            assign c = prod <<< -rshift;
        end
    endgenerate
endmodule
