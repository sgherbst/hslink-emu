`timescale 1ns/1ps

import signal_package::*;
import rx_package::*;

module comp_async (
    input COMP_IN_FORMAT in,
    output out
);

    assign out = (in >= $signed(0)) ? 1'b1 : 1'b0;

endmodule
