`timescale 1ns/1ps

import time_package::*;
import rx_package::*;

module rx_clock #(
    parameter lfsr_init = 3
)(
    input wire clk,
    input wire rst,
    input TIME_FORMAT time_next,
    input DCO_CODE_FORMAT code,
    output TIME_FORMAT time_clock,
    output wire [1:0] cke_out,
    output wire time_eq
);
    // PWL instantiation
    RX_DCO_OUT_FORMAT rx_dco_pwl_out; // this is signed...

    pwl #(
        // note: setting_width=0 to indicate there
        // are not multiple settings
        .setting_width(0),
        
        // note: address offset is zero because 
        // DCO codes start at 0 and go up to (1<<DCO_CODE_WIDTH)-1
        .addr_offset(0),

        // handle bias value, which is specified as a parameter rather
        // than as a ROM
        .bias_width(RX_DCO_BIAS_WIDTH),
        .bias_val(RX_DCO_BIAS_VAL),

        .segment_rom_name(RX_DCO_ROM_NAME),
        .in_width(DCO_CODE_WIDTH),
        .in_point(DCO_CODE_POINT),
        .addr_width(RX_DCO_ADDR_WIDTH),
        .segment_width(RX_DCO_SEGMENT_WIDTH),
        .offset_width(RX_DCO_OFFSET_WIDTH),
        .slope_width(RX_DCO_SLOPE_WIDTH),
        .slope_point(RX_DCO_SLOPE_POINT),
        .out_width(RX_DCO_OUT_WIDTH),
        .out_point(RX_DCO_OUT_POINT)
    ) dco_pwl (
        .in(code), 
        .out(rx_dco_pwl_out),
        .clk(clk),
        .rst(rst),
        // setting input is not used, but SystemVerilog
        // does not provide a mechanism to indicate an
        // unused port.  to a bogus warning, the port
        // is driven with a signal of the appropriate
        // width [-1:0] => 2 bits wide
        .setting(2'b00)
    );

    // the period is the unsigned version of the PWL output
    DCO_PERIOD_FORMAT period;
    assign period = rx_dco_pwl_out[DCO_PERIOD_WIDTH-1:0];

    // instantiate the clock
    clock #(
        .N(2),
        .PERIOD_WIDTH(DCO_PERIOD_WIDTH),
        .JITTER_WIDTH(RX_JITTER_WIDTH),
        .UPDATE_WIDTH(RX_UPDATE_WIDTH),
        .lfsr_init(lfsr_init)
    ) clock_i(.clk(clk), 
        .rst(rst),
        .time_next(time_next),
        .period(period),
        .time_clock(time_clock),
        .cke_out(cke_out),
        .time_eq(time_eq)
    );

endmodule
