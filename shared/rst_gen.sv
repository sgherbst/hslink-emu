`timescale 1ns/1ps

module rst_gen #(
    parameter n=1
) (
    input wire clk,
    input wire rst_in,
    input wire [n-1:0] cke,
    output wire [n-1:0] rst_out
);
    genvar k;
    generate
        for (k=0; k<n; k=k+1) begin : rst_gen_blk
            my_dff_cke #(
                .init(1'b1)
            ) rst_gen_dff (
                .d(1'b0),
                .q(rst_out[k]),
                .clk(clk),
                .rst(rst_in),
                .cke(cke[k])
            );
        end
    endgenerate
endmodule
