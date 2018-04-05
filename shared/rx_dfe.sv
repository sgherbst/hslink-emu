`timescale 1ns/1ps

module rx_dfe #(
    parameter N=1,
    parameter real coeffs [0:N-1] = {1.0},
    parameter sig_bits=1,
    parameter sig_res_bits=1
)(
    input signed [sig_bits-1:0] in,
    input data,
    input clk,
    output wire signed [sig_bits-1:0] out
);
    // verilog idiosyncracy needed to initialize hist array
    localparam signed [sig_bits-1:0] hist_zero=0;   

    wire signed [sig_bits-1:0] weights [0:N-1];
    genvar k;
    generate
        for (k=0; k<N; k=k+1) begin : weight_gen_block
            assign weights[k] = (data==1'b1) ? longint'(real'(coeffs[k])*(real'(2)**real'(sig_res_bits))) : longint'(real'(-coeffs[k])*(real'(2)**real'(sig_res_bits)));
        end            
        if (N==1) begin : out_assign_n_eq_1
            assign out = in + weights[0];
        end else if (N>1) begin : out_assign_n_gt_1
            // history declaration and initialization
            reg signed [sig_bits-1:0] hist[0:N-2] = '{(N-1){hist_zero}};

            // filter state update
            for (k=0; k<N-2; k=k+1) begin
                always @(posedge clk) begin
                    hist[k] <= hist[k+1] + weights[k+1];
                end
            end
            always @(posedge clk) begin
                hist[N-2] <= weights[N-1];
            end

            // output assignment
            assign out = in + weights[0] + hist[0];
        end else begin : out_assign_err_condition
            $error("Only N>=1 supported.");
        end
    endgenerate 
endmodule
