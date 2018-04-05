`timescale 1ns/1ps

module mysum #(
    parameter in_bits=1,
    parameter in_terms=1,
    parameter out_bits=1
) (
    input wire signed [in_bits-1:0] in [in_terms-1:0],
    output reg signed [out_bits-1:0] out
);
    // reference: https://stackoverflow.com/questions/17159397/verilog-adding-individual-bits-of-a-register-combinational-logic-register-wid
    always_comb begin
        out = '0; // fill 0
        foreach(in[i]) begin
            out += in[i];
        end
    end
endmodule
