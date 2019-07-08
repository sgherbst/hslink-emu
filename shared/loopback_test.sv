`timescale 1ns/1ps

module loopback_test (
    // RX and TX clock+data
    input wire logic out_tx,
    input wire logic cke_tx,
    input wire logic out_rx,
    input wire logic cke_rx,

    // analysis outputs
    output var logic [31:0] rx_good_bits,
    output var logic [31:0] rx_bad_bits,
    output var logic [31:0] rx_total_bits,

    // control
    input wire logic [2:0] run_state,
    input wire logic [7:0] loopback_offset,

    // clock and reset
    input wire logic clk,
    input wire logic rst
);

    // TODO: move to a package

    localparam [2:0] IN_RESET   =   3'b100;
    localparam [2:0] WAITING    =   3'b000;
    localparam [2:0] RUNNING    =   3'b010;
    localparam [2:0] DONE       =   3'b001;

    // Delay clock enables by one cycle to allow for proper sampling

    logic cke_tx_d, cke_rx_d;
    always @(posedge clk) begin
        if (rst == 1'b1) begin
            cke_tx_d <= 1'b0;
            cke_rx_d <= 1'b0;
        end else begin
            cke_tx_d <= cke_tx;
            cke_rx_d <= cke_rx;
        end
    end

    // Total bit counter

    always @(posedge clk) begin
        if (rst == 1'b1) begin
            rx_total_bits <= 'd0;
        end else if ((run_state == RUNNING) && (cke_rx_d == 1'b1)) begin
            rx_total_bits <= rx_total_bits + 'd1;
        end else begin
            rx_total_bits <= rx_total_bits;
        end
    end

    // Address logic

    logic [7:0] wr_addr;
    logic [7:0] rd_addr;
    logic [7:0] offset;

    always @(posedge clk) begin
        if (rst == 1'b1) begin
            wr_addr <= 'd0;
        end else if (cke_tx_d == 1'b1) begin
            wr_addr <= wr_addr + 'd1;
        end else begin
            wr_addr <= wr_addr;
        end
    end

    assign rd_addr = wr_addr - loopback_offset;

    // Dual-port BRAM logic

    logic mem [255:0];
    logic mem_out;

    always @(posedge clk) begin
        if (cke_tx_d == 1'b1) begin
            mem[wr_addr] <= out_tx;
        end
    end

    always @(posedge clk) begin
        mem_out <= mem[rd_addr];
    end

    // Comparison logic

    logic match;
    assign match = (mem_out == out_rx) ? 1'b1 : 1'b0;

    always @(posedge clk) begin
        if (rst == 1'b1) begin
            rx_good_bits <= 'd0;
            rx_bad_bits <= 'd0;
        end else if ((run_state == RUNNING) && (cke_rx_d == 1'b1)) begin
            if (match == 1'b1) begin
                rx_good_bits <= rx_good_bits + 'd1;
                rx_bad_bits <= rx_bad_bits;
            end else begin
                rx_good_bits <= rx_good_bits;
                rx_bad_bits <= rx_bad_bits + 'd1;
            end
        end else begin
            rx_good_bits <= rx_good_bits;
            rx_bad_bits <= rx_bad_bits;
        end
    end

endmodule