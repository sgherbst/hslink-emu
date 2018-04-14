import time_package::*;
import path_package::*;
import signal_package::*;

module ila_0 (
    input wire clk,
    input probe0,
    input TIME_FORMAT probe1,
    input probe2,
    input FILTER_IN_FORMAT probe3,
    input probe4
);

    integer f;
    initial begin
        f = $fopen({DATA_DIR, "/", "tx", ".txt"}, "w");
    end

    always @(posedge clk) begin
        // write time, value pair to file
        if (!(^probe1===1'bx)) begin
            $fwrite(f,
                    "%0.9e,\t%0.9e\n", 
                    real'(probe1)/(real'(2)**real'(TIME_POINT)),
                    real'(probe3)/(real'(2)**real'(FILTER_IN_POINT)));
        end
    end

endmodule
