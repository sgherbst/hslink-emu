import time_package::*;

module adc #(
    parameter name = "adc",
    parameter ext = ".txt",
    parameter sig_bits = 1,
    parameter sig_point = 1
)(
    input wire clk,
    input TIME_FORMAT time_curr,
    input wire signed [sig_bits-1:0] sig
);
    integer f;
    initial begin
        f = $fopen({name, ext}, "w");
    end

    TIME_FORMAT time_samp;
    reg signed [sig_bits-1:0] sig_samp;

    always @(posedge clk) begin
        // sample time and value
        time_samp <= time_curr;
        sig_samp <= sig;

        // write time, value pair to file
        if (!(^time_curr===1'bx)) begin
            $fwrite(f,
                    "%0.9e,\t%0.9e\n", 
                    real'(time_curr)/(real'(2)**real'(TIME_POINT)),
                    real'(sig)/(real'(2)**real'(sig_point)));
        end
    end
endmodule
