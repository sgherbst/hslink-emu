// reference: code by B.C. Lim for DAC17 (digital_lf)

`timescale 1ns/1ps

module digital_lf #(
    parameter N = 14,                                                // width of output
    parameter [N-1:0] init = longint'(1)<<(longint'(N)-longint'(1)), // starting state of the filter
    parameter integer Kp=256,                                        // proportional gain
    parameter integer Ki=1                                           // integral gain
)(
    input clk,                      // triggering clock
    input up,                       // up signal from phase detector
    input dn,                       // down signal from phase detector
    output reg [N-1:0] out = init   // output signal
);
    // save previous state of the inputs
    wire [1:0] curr = {up, dn};
    reg [1:0] prev = 2'b00;
    always @(posedge clk) begin
        prev <= curr;
    end
    
    // combo logic for term a
    reg signed [N-1:0] a;
    always_comb begin
        case (curr)
            2'b00 : a = 0;         // up=0, dn=0 => (up-dn) = 0
            2'b01 : a = -(Ki+Kp);  // up=0, dn=1 => (up-dn) = -1
            2'b10 : a = +(Ki+Kp);  // up=1, dn=0 => (up-dn) = +1
            2'b11 : a = 0;         // up=1, dn=1 => (up-dn) = 0
        endcase
    end

    // combo logic for term b
    reg signed [N-1:0] b;
    always_comb begin
        case (prev)
            2'b00 : b = 0;   // up=0, dn=0 => (up-dn) = 0
            2'b01 : b = +Kp; // up=0, dn=1 => (up-dn) = -1
            2'b10 : b = -Kp; // up=1, dn=0 => (up-dn) = +1
            2'b11 : b = 0;   // up=1, dn=1 => (up-dn) = 0
        endcase
    end

    // state update logic
    always @(posedge clk) begin
        out <= out + a + b;
    end
endmodule
