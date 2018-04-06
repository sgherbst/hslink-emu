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
    integer f;
    initial begin
        f = $fopen({name, ext}, "w");
    end

    reg [time_bits-1:0] time_samp;
    reg signed [sig_bits-1:0] sig_samp;

    always @(posedge clk) begin
        // sample time and value
        time_samp <= time_curr;
        sig_samp <= sig;

        // write time, value pair to file
        if (!(^time_curr===1'bx)) begin
            $fwrite(f, "%0.9e,\t%0.9e\n", real'(time_curr)/(real'(2)**real'(time_point)), real'(sig)/(real'(2)**real'(sig_point)));
        end
    end
endmodule
