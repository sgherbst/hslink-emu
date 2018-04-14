// reference: code by B.C. Lim for DAC17 (alexander_pd)
// see also slide 21: https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-976-high-speed-communication-circuits-and-systems-spring-2003/lecture-notes/lec21.pdf

`timescale 1ns/1ps

import signal_package::*;
import rx_package::*;

module bbpd (
    input COMP_IN_FORMAT in,
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
    comp_sync comp_p(.in(in), .clk(clk_p), .rst(rst_p), .out(data));
    comp_sync comp_n(.in(in), .clk(clk_n), .rst(rst_n), .out(t));

    // logic used for output assignment
    wire a, b;
    my_dff #(
        .n(2)
    ) my_dff_i (
        .d({data, t}),
        .q({   a, b}),
        .clk(clk_p),
        .rst(rst_p)
    );

    // output assignments
    assign up = a ^ b;
    assign dn = data ^ b;

endmodule
