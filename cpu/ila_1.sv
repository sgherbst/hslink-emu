import time_package::*;
import path_package::*;
import signal_package::*;

module ila_1 (
    input wire clk,
    input probe0,
    input TIME_FORMAT probe1,
    input probe2,
    input FILTER_OUT_FORMAT probe3,
    input DFE_OUT_FORMAT probe4,
    input COMP_IN_FORMAT probe5,
    input DCO_CODE_FORMAT probe6,
    input probe7
);

    integer f;
    initial begin
        f = $fopen({DATA_DIR, "/", "rxp", ".txt"}, "w");
    end

    always @(posedge clk) begin
        // write time, value pair to file
        if (!(^probe1===1'bx)) begin
            $fwrite(f,
                    "%0.9e,\t%0.9e\n", 
                    real'(probe1)/(real'(2)**real'(TIME_POINT)),
                    real'(probe3)/(real'(2)**real'(FILTER_OUT_POINT)));
        end
    end

endmodule
