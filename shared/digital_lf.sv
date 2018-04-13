// reference: code by B.C. Lim for DAC17 (digital_lf)

`timescale 1ns/1ps

module digital_lf #(
    parameter N = 14                     // width of output
)(
    input wire clk,                      // triggering clock
    input wire rst,                      // reset signal
    input wire [N-1:0] init,             // initialization signal
    input wire up,                       // up signal from phase detector
    input wire dn,                       // down signal from phase detector
    input wire signed [N-1:0] kp,        // proportional gain
    input wire signed [N-1:0] ki,        // integral gain
    output reg [N-1:0] out               // output signal
);
    // compute up minus down
    wire signed [1:0] curr = $signed({1'b0, up}) - $signed({1'b0, dn});

    // save previous state of the inputs
    reg signed [1:0] prev;
    my_dff #(
        .n(2)
    ) prev_dff (
        .d(curr),
        .q(prev),
        .clk(clk),
        .rst(rst)
    );

    // compute first update term
    wire signed [N-1:0] ki_plus_kp = ki + kp;
    wire signed [N-1:0] a = curr * ki_plus_kp;

    // compute second update term
    wire signed [N-1:0] b = prev * kp;   

    // state update logic
    always @(posedge clk) begin
        if (rst == 1'b1) begin
            out <= init;
        end else begin
            out <= out + a - b;
        end
    end
endmodule
