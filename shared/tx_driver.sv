`timescale 1ns/1ps

import signal_settings::signal_t;
import signal_settings::SIGNAL_POINT;

module tx_driver (
    input in,
    input clk,
    output signal_t out
);
    localparam longint one = longint'(real'(1)*(real'(2)**real'(SIGNAL_POINT)));
    localparam longint zero = longint'(real'(-1)*(real'(2)**real'(SIGNAL_POINT)));

    assign out = in ? one : zero;
endmodule
