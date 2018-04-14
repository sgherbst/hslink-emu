`timescale 1ns/1ps

import time_package::*;
import signal_package::*;
import filter_package::*;
import tx_package::*;
import rx_package::*;

module dut #(
    parameter USE_VIO=1
)(
    input wire SYSCLK_P,
    input wire SYSCLK_N,
    output reg time_flag,

    // I/O covered by VIO on FPGA
    input wire rst_ext,
    input wire [RX_SETTING_WIDTH-1:0] rx_setting_ext,
    input wire [TX_SETTING_WIDTH-1:0] tx_setting_ext,
    input DCO_CODE_FORMAT dco_init_ext,
    input signed [DCO_CODE_WIDTH-1:0] ki_lf_ext,
    input signed [DCO_CODE_WIDTH-1:0] kp_lf_ext,
    input TIME_FORMAT time_trig_ext,
    input TX_JITTER_SCALE_FORMAT jitter_scale_tx_ext,
    input RX_JITTER_SCALE_FORMAT jitter_scale_rx_ext
);
    //////////////////////
    // Debug signals
    //////////////////////

    // Debug: TX
    wire clk_tx;
    wire rst_tx;
    TIME_FORMAT time_curr;
    wire out_tx;
    FILTER_IN_FORMAT filter_in;
    ila_0 ila_0_i(
        .clk(clk_tx),
        .probe0(rst_tx),
        .probe1(time_curr),
        .probe2(out_tx),
        .probe3(filter_in),
        .probe4(time_flag)
    );

    // Debug: RX P
    wire clk_rx_p;
    wire rst_rx_p; 
    wire out_rx;
    FILTER_OUT_FORMAT filter_out;
    DFE_OUT_FORMAT dfe_out;
    COMP_IN_FORMAT comp_in;
    DCO_CODE_FORMAT dco_code;
    ila_1 ila_1_i(
        .clk(clk_rx_p),
        .probe0(rst_rx_p),
        .probe1(time_curr),
        .probe2(out_rx),
        .probe3(filter_out),
        .probe4(dfe_out),
        .probe5(comp_in),
        .probe6(dco_code),
        .probe7(time_flag)
    );

    // Debug: RX N
    wire clk_rx_n;
    wire rst_rx_n;
    ila_2 ila_2_i (
        .clk(clk_rx_n),
        .probe0(rst_rx_n),
        .probe1(time_curr),
        .probe2(filter_out),
        .probe3(time_flag)
    );

    // Clock generation code
    wire cke_tx;
    wire cke_rx_p;
    wire cke_rx_n;
    wire clk_sys;
    clkgen clkgen_i(
        .SYSCLK_P(SYSCLK_P),
        .SYSCLK_N(SYSCLK_N), 
        .clk_sys(clk_sys),
        .clk_tx(clk_tx),
        .cke_tx(cke_tx),
        .clk_rx_p(clk_rx_p),
        .cke_rx_p(cke_rx_p),
        .clk_rx_n(clk_rx_n),
        .cke_rx_n(cke_rx_n)
    );

    // DUT I/O                    
    wire rst;
    wire [RX_SETTING_WIDTH-1:0] rx_setting;
    wire [TX_SETTING_WIDTH-1:0] tx_setting;
    DCO_CODE_FORMAT dco_init;
    wire signed [DCO_CODE_WIDTH-1:0] kp_lf;
    wire signed [DCO_CODE_WIDTH-1:0] ki_lf;
    TIME_FORMAT time_trig;
    TX_JITTER_SCALE_FORMAT jitter_scale_tx;
    RX_JITTER_SCALE_FORMAT jitter_scale_rx;

    // VIO
    generate
        if (USE_VIO == 1) begin
            vio_0 vio_0_i (
                .clk(clk_sys),
                .probe_out0(rst),
                .probe_out1(rx_setting),
                .probe_out2(tx_setting),
                .probe_out3(dco_init),
                .probe_out4(kp_lf),
                .probe_out5(ki_lf),
                .probe_out6(time_trig),
                .probe_out7(jitter_scale_tx),
                .probe_out8(jitter_scale_rx)
            );
        end else begin
            assign rst = rst_ext;
            assign rx_setting = rx_setting_ext;
            assign tx_setting = tx_setting_ext;
            assign dco_init = dco_init_ext;
            assign kp_lf = kp_lf_ext;
            assign ki_lf = ki_lf_ext;
            assign time_trig = time_trig_ext;
            assign jitter_scale_tx = jitter_scale_tx_ext;
            assign jitter_scale_rx = jitter_scale_rx_ext;
        end
    endgenerate

    // reset generators
    wire rst_sys;
    rst_gen #(
        .n(4)
    ) rst_gen_i (
        .clk(clk_sys),
        .rst_in(rst),
        .cke(    {   1'b1, cke_tx, cke_rx_p, cke_rx_n}),
        .rst_out({rst_sys, rst_tx, rst_rx_p, rst_rx_n})
    );
        
    // Time management
    TIME_FORMAT time_in [0:1];
    TIME_FORMAT time_next;
    wire time_eq_tx, time_eq_rx;

    // Create TX clock
    tx_clock tx_clk_i(
        .clk(clk_sys),
        .rst(rst_sys),
        .time_next(time_next),
        .jitter_scale(jitter_scale_tx),
        .time_clock(time_in[0]),
        .cke_out(cke_tx),
        .time_eq(time_eq_tx)
    );

    // Create random data generator
    prbs prbs_i(
        .out(out_tx),
        .clk(clk_tx),
        .rst(rst_tx)
    );

    // Drive data into channel
    tx_ffe tx_ffe_i(
        .in(out_tx),
        .out(filter_in),
        .tx_setting(tx_setting),
        .clk(clk_tx),
        .rst(rst_tx)
    );

    // Filter data stream according to channel + CTLE dynamics
    filter filter_i(
        .in(filter_in),
        .time_eq_in(time_eq_tx),
        .out(filter_out),
        .time_next(time_next),
        .rx_setting(rx_setting),
        .clk(clk_sys),
        .rst(rst_sys)
    );

    // Add DFE correction
    rx_dfe rx_dfe_i(
        .in(out_rx),
        .clk(clk_rx_p),
        .rst(rst_rx_p),
        .tx_setting(tx_setting),
        .rx_setting(rx_setting),
        .out(dfe_out)
    );
    assign comp_in = filter_out + dfe_out;

    // Bang-band phase detector
    wire up, dn;
    bbpd bbpd_i(
        .in(comp_in),
        .clk_p(clk_rx_p),
        .rst_p(rst_rx_p),
        .clk_n(clk_rx_n),
        .rst_n(rst_rx_n),
        .data(out_rx),
        .up(up),
        .dn(dn)
    );

    // Digital loop filter
    digital_lf #(
        .N(DCO_CODE_WIDTH)
    ) digital_lf_i(
        .clk(clk_rx_p),
        .rst(rst_rx_p),
        .up(up),
        .dn(dn),
        .out(dco_code),
        .init(dco_init),
        .ki(ki_lf),
        .kp(kp_lf)
    );

    // Create RX clock
    rx_clock rx_clk_i (
        .code(dco_code),
        .time_next(time_next),
        .jitter_scale(jitter_scale_rx),
        .time_clock(time_in[1]),
        .cke_out({cke_rx_p, cke_rx_n}),
        .time_eq(time_eq_rx),
        .clk(clk_sys),
        .rst(rst_sys)
    );

    // Create time manager
    time_manager #(
        .N(2)
    ) tm (
        .time_in(time_in),
        .time_next(time_next),
        .time_curr(time_curr),
        .clk(clk_sys),
        .rst(rst_sys)
    );

    // Monitor time
    always @(posedge clk_sys) begin
        if (rst == 1'b1) begin
            time_flag <= 1'b0;
        end else if (time_curr >= time_trig) begin
            time_flag <= 1'b1;
        end else begin
            time_flag <= time_flag;
        end
    end

endmodule
