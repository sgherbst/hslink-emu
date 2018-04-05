// reference: code by B.C. Lim for DAC17 (alexander_pd)
// see also slide 21: https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-976-high-speed-communication-circuits-and-systems-spring-2003/lecture-notes/lec21.pdf

`timescale 1ns/1ps

module bbpd #(
    parameter sig_bits = 1
) (
    input signed [sig_bits-1:0] in,
    input clk, 
    input clkb,
    output data,
    output up,
    output dn
);

    // sample data
    wire t;
    comp #(.sig_bits(sig_bits)) comp_p(.in(in),  .clk(clk), .out(data));
    comp #(.sig_bits(sig_bits)) comp_n(.in(in), .clk(clkb),    .out(t));

    // logic used for logic assignment
    reg a=1'b0;
    reg b=1'b0;

    always @(posedge clk) begin
        a <= data;
        b <= t;
    end

    // output assignments
    assign up = a ^ b;
    assign dn = data ^ b;

endmodule
