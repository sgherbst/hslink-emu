`timescale 1ns/1ps

module my_rom_async #(
    parameter addr_bits = 1,
    parameter data_bits = 1,
    parameter filename = "rom.mem"
)(
    input wire [addr_bits-1:0] addr,
    output reg [data_bits-1:0] dout
);
    localparam longint rom_length = longint'(1)<<longint'(addr_bits);
    
    // initialize ROM
    reg [data_bits-1:0] rom [rom_length];
    initial begin
        $readmemb(filename, rom);
    end

    // read from ROM
    always_comb begin
        dout = rom[addr];
    end
endmodule
