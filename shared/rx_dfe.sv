`timescale 1ns/1ps

import path_package::*;
import tx_package::*;
import rx_package::*;
import filter_package::*;

module rx_dfe (
    input in,
    input clk,
    input rst,
    input [TX_SETTING_WIDTH-1:0] tx_setting,
    input [RX_SETTING_WIDTH-1:0] rx_setting,
    output DFE_OUT_FORMAT out
);
    localparam rom_addr_width = TX_SETTING_WIDTH + RX_SETTING_WIDTH + N_DFE_TAPS;

    // instantiate the ROM
    wire [rom_addr_width-1:0] rom_addr;
    wire [DFE_OUT_WIDTH-1:0] rom_data;
    my_rom_async #(
        .addr_bits(rom_addr_width),
        .data_bits(DFE_OUT_WIDTH),
        .filename({ROM_DIR, "/", RX_DFE_ROM_NAME})
    ) myrom_i (
        .addr(rom_addr),
        .dout(rom_data)
    );

    // store the input history
    wire [N_DFE_TAPS-2:0] in_hist;
    my_dff #(
        .n(N_DFE_TAPS-1)
    ) my_dff_i (
        .d((in_hist << 1) | in),
        .q(in_hist),
        .clk(clk),
        .rst(rst)
    );

    // set the ROM address
    assign rom_addr = {tx_setting, rx_setting, in_hist, in};

    // write the output
    assign out = $signed(rom_data & {DFE_OUT_WIDTH{~rst}});

endmodule
