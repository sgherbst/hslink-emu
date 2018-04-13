// reference: code by B.C. Lim for DAC17 (alexander_pd)
// see also slide 21: https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-976-high-speed-communication-circuits-and-systems-spring-2003/lecture-notes/lec21.pdf

`timescale 1ns/1ps

import signal_package::*;

module bbpd (
    input FILTER_OUT_FORMAT in,
    input clk_p, 
    input clk_n,
    input rst_p,
    input rst_n,
    output data,
    output up,
    output dn
);

    // sample data
    wire t;
    comp comp_p(.in(in), .clk(clk_p), .rst(rst_p), .out(data));
    comp comp_n(.in(in), .clk(clk_n), .rst(rst_n), .out(t));

    // logic used for output assignment
    reg a, b;
    always @(posedge clk_p) begin
        if (rst_p == 1'b1) begin
            a <= 1'b0;
            b <= 1'b0;
        end else begin
            a <= data;
            b <= t;
        end
    end

    // output assignments
    assign up = a ^ b;
    assign dn = data ^ b;

endmodule
