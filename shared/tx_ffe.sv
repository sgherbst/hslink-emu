`timescale 1ns/1ps

import filter_package::*;
import tx_package::*;
import signal_package::*;
import path_package::*;

module tx_ffe (
    input in,
    input clk,
    input rst,
    output FILTER_IN_FORMAT out,
    input [TX_SETTING_WIDTH-1:0] tx_setting
);
    localparam rom_addr_width = TX_SETTING_WIDTH + N_TX_TAPS;

    // instantiate the ROM
    wire [rom_addr_width-1:0] rom_addr;
    wire [FILTER_IN_WIDTH-1:0] rom_data;
    my_rom_sync #(
        .addr_bits(rom_addr_width),
        .data_bits(FILTER_IN_WIDTH),
        .filename({ROM_DIR, "/", TX_FFE_ROM_NAME})
    ) myrom_i (
        .addr(rom_addr),
        .dout(rom_data),
        .clk(clk)
    );

    // store the input history
    wire [N_TX_TAPS-2:0] in_hist;
    my_dff #(
        .n(N_TX_TAPS-1)
    ) my_dff_i (
        .d((in_hist << 1) | in),
        .q(in_hist),
        .clk(clk),
        .rst(rst)
    );

    // set the ROM address
    assign rom_addr = {tx_setting, in_hist, in};

    // write the output
    assign out = $signed(rom_data & {FILTER_IN_WIDTH{~rst}});
endmodule
