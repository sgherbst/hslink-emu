`timescale 1ns/1ps

module mysum #(
    parameter in_bits=1,
    parameter in_terms=1,
    parameter out_bits=1
) (
    input wire signed [in_bits-1:0] in [in_terms],
    output reg signed [out_bits-1:0] out
);
    // reference: https://stackoverflow.com/questions/26488295/is-there-a-way-to-sum-multi-dimensional-arrays-in-verilog
    integer idx;
    always @* begin
        out = 0;
        for (idx=0; idx<in_terms; idx=idx+1) begin
            out = out + in[idx];
        end
    end
endmodule
