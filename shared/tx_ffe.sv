`timescale 1ns/1ps

import globals::*;
import filter_package::*;
import tx_package::*;
import signal_package::*;

module tx_ffe (
    input in,
    input clk,
    input rst,
    output FILTER_IN_FORMAT out,
    input [TX_SETTING_WIDTH-1:0] tx_setting
);
    localparam rom_addr_width = TX_SETTING_WIDTH + N_TAPS;

    // instantiate the ROM
    wire [rom_addr_width-1:0] rom_addr;
    wire [FILTER_IN_WIDTH-1:0] rom_data;
    myrom #(.addr_bits(rom_addr_width),
            .data_bits(FILTER_IN_WIDTH),
            .filename({ROM_DIR_PATH, TX_FFE_ROM_NAME})) myrom_i(.addr(rom_addr), .dout(rom_data), .clk(clk));

    // store the input history
    reg [N_TAPS-2:0] in_hist;
    always @(posedge clk) begin
        if (rst == 1'b1) begin
            in_hist <= 0;
        end else begin
            in_hist <= (in_hist << 1) | in;
        end
    end

    // set the ROM address
    assign rom_addr = {tx_setting, in_hist, in};

    // POR mask
    reg valid_mask;
    always @(posedge clk) begin
        if (rst == 1'b1) begin
            valid_mask <= 1'b0;
        end else begin
            valid_mask <= 1'b1;
        end
    end

    // write the output
    assign out = $signed(rom_data & {FILTER_IN_WIDTH{valid_mask}});
endmodule
