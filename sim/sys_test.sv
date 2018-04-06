`timescale 1ns/1ps

module tb;
    wire sim_done;
    reg SYSCLK_P = 1'b0;
    reg SYSCLK_N = 1'b1;

    initial begin
        forever begin
            SYSCLK_P = 1'b0;
            SYSCLK_N = 1'b1;
            #2.5;
            SYSCLK_P = 1'b1;
            SYSCLK_N = 1'b0;
            #2.5;
        end
    end

    dut dut_i(.SYSCLK_P(SYSCLK_P), .SYSCLK_N(SYSCLK_N), .sim_done(sim_done));

    always @(sim_done) begin
        if (sim_done == 1'b1) begin
            $finish;
        end
    end
endmodule
