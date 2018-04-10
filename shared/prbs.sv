`timescale 1ns/1ps

// reference: https://www.xilinx.com/support/documentation/application_notes/xapp210.pdf
module prbs #(
    parameter init=2
)(
    input wire clk,
    input wire rst,
    output out
);
    reg [15:0] state;
    assign out = state[0];
    
    always @(posedge clk) begin
        if (rst == 1'b1) begin
            state <= init;
        end else begin
            state <= {state[14:0], ~state[15]^state[14]^state[12]^state[3]};
        end
    end
endmodule
