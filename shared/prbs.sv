`timescale 1ns/1ps

// reference: https://www.xilinx.com/support/documentation/application_notes/xapp210.pdf
module prbs #(
    parameter init=2
)(
    input wire clk,
    output reg out
);
    reg [15:0] state = init;
//    assign out = state[0];
    assign out = 1;
    
    always @(posedge clk) begin
        state <= {state[14:0], ~state[15]^state[14]^state[12]^state[3]};
    end
endmodule
