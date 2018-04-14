`timescale 1ns/1ps

import signal_package::*;
import rx_package::*;

module comp_sync (
    input COMP_IN_FORMAT in,
    input clk,
    input rst,
    output out
);

    // instantiate asynchronous comparator
    wire comp_async_out;
    comp_async comp_async_i(
        .in(in),
        .out(comp_async_out)
    );

    // sample asynchronous comparator output
    my_dff my_dff_i(
        .d(comp_async_out),
        .q(out),
        .clk(clk),
        .rst(rst)
    );

endmodule
