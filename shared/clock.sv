`timescale 1ns/1ps

import time_package::TIME_FORMAT;

module clock #(
    parameter integer N = 1,
    parameter integer TIME_INC_BITS = 1,
    parameter integer JITTER_WIDTH = 1,
    parameter lfsr_init = 1
)(
    input wire clk,
    input wire rst,
    input TIME_FORMAT time_next,
    input wire [TIME_INC_BITS-1:0] inc,
    output TIME_FORMAT time_clock,
    output reg [N-1:0] cke_out,
    output wire time_eq
);
    // clock gating signal
    assign time_eq = (time_next == time_clock) ? 1'b1 : 1'b0;

    // lfsr for jitter
    wire [JITTER_WIDTH-1:0] jitter;
    lfsr #(.n(JITTER_WIDTH), .init(lfsr_init)) lfsr_i(.clk(clk), .cke(time_eq), .rst(rst), .state(jitter));

    // clock period progression logic
    always @(posedge clk) begin
        if (rst == 1'b1) begin
            time_clock <= 0;
        end else if (time_eq == 1'b1) begin
            time_clock <= time_clock + inc + jitter;
        end else begin
            time_clock <= time_clock;
        end
    end

    // clock gating logic
    wire [N-1:0] clk_en;

    // treat one- and two- phase differently
    generate
        if (N==1) begin : one_phase
            assign clk_en = time_eq;
        end else if (N==2) begin : two_phase
            reg mask;
            always @(posedge clk) begin
                if (rst == 1'b1) begin
                    mask <= 0;
                end else if (time_eq == 1'b1) begin
                    mask <= ~mask;
                end else begin
                    mask <= mask;
                end
            end
            assign clk_en[0] = time_eq & mask;
            assign clk_en[1] = time_eq & (~mask);
        end else begin : illegal_phase
            $error("Only N=1 and N=2 are supported at this time.");
        end
    endgenerate

    // delay clock enable by one cycle
    always @(posedge clk) begin
        if (rst == 1'b1) begin
            cke_out <= 0;
        end else begin
            cke_out <= clk_en;
        end 
    end
endmodule
