`timescale 1ns/1ps

module adc #(
    parameter name = "adc",
    parameter ext = ".txt",
    parameter sig_bits = 1,
    parameter sig_point = 1,
    parameter time_bits = 1,
    parameter time_point = 1
)(
    input wire clk,
    input wire [time_bits-1:0] time_curr,
    input wire signed [sig_bits-1:0] sig
);
    (* dont_touch = "true" *) reg [time_bits-1:0] time_samp;
    (* dont_touch = "true" *) reg [sig_bits-1:0] sig_samp;

    always @(posedge clk) begin
        time_samp <= time_curr;
        sig_samp <= sig;
    end
endmodule
