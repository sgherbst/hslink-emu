// reference: code by B.C. Lim for DAC17 (alexander_pd)
// see also slide 21: https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-976-high-speed-communication-circuits-and-systems-spring-2003/lecture-notes/lec21.pdf

`timescale 1ns/1ps

import signal_package::*;

module bbpd (
    input FILTER_OUT_FORMAT in,
    input clk, 
    input clkb,
    output data,
    output up,
    output dn
);

    // sample data
    wire t;
    comp comp_p(.in(in),  .clk(clk), .out(data));
    comp comp_n(.in(in), .clk(clkb),    .out(t));

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
