import time_package::*;
import path_package::*;
import signal_package::*;

module ila_2 (
    input wire clk,
    input probe0,
    input TIME_FORMAT probe1,
    input FILTER_OUT_FORMAT probe2,
    input [2:0] probe3
);

    `ifndef SIM_PROFILE

    integer f;
    initial begin
        f = $fopen({DATA_DIR, "/", "rxn", ".txt"}, "w");
    end

    always @(posedge clk) begin
        // write time, value pair to file
        if (!(^probe1===1'bx)) begin
            $fwrite(f,
                    "%0.9e,\t%0.9e\n", 
                    real'(probe1)/(real'(2)**real'(TIME_POINT)),
                    real'(probe2)/(real'(2)**real'(FILTER_OUT_POINT)));
        end
    end

    `endif

endmodule
