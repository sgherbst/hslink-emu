`timescale 1ns/1ps

import time_package::*;
import signal_package::*;
import filter_package::*;
import tx_package::*;

module dut #(
    parameter USE_VIO=1,
    parameter USE_ADC=0
)(
    input wire [RX_SETTING_WIDTH-1:0] rx_setting_ext,
    input wire [TX_SETTING_WIDTH-1:0] tx_setting_ext,
    input wire rst_ext,
    input wire SYSCLK_P,
    input wire SYSCLK_N,
    output wire sim_done
);
    // Clock generation code
    (* mark_debug = "true" *) wire cke_tx;
    (* mark_debug = "true" *) wire cke_rx_p;
    (* mark_debug = "true" *) wire cke_rx_n;
    wire clk_sys, clk_tx, clk_rx_p, clk_rx_n;
    clkgen clkgen_i(.SYSCLK_P(SYSCLK_P),
                    .SYSCLK_N(SYSCLK_N), 
                    .clk_sys(clk_sys),
                    .clk_tx(clk_tx),
                    .cke_tx(cke_tx),
                    .clk_rx_p(clk_rx_p),
                    .cke_rx_p(cke_rx_p),
                    .clk_rx_n(clk_rx_n),
                    .cke_rx_n(cke_rx_n));

    // DUT I/O                    
    wire [RX_SETTING_WIDTH-1:0] rx_setting;
    wire [TX_SETTING_WIDTH-1:0] tx_setting;
    wire rst;

    // VIO
    generate
        if (USE_VIO == 1) begin
            vio_0 vio_0_i (
                .clk(clk_sys),
                .probe_out0(rst),
                .probe_out1(rx_setting),
                .probe_out2(tx_setting)
            );
        end else begin
            assign rx_setting = rx_setting_ext;
            assign tx_setting = tx_setting_ext;
            assign rst = rst_ext;
        end
    endgenerate

    // rst_sys generator 
    (* mark_debug = "true" *) reg rst_sys;
    always @(posedge clk_sys) begin
        if (rst == 1'b1) begin
            rst_sys <= 1'b1;
        end else begin
            rst_sys <= 1'b0;
        end
    end
    
    // rst_tx generator
    (* mark_debug = "true" *) reg rst_tx;
    always @(posedge clk_sys) begin
        if (rst == 1'b1) begin
            rst_tx <= 1'b1;
        end else if (cke_tx == 1'b1) begin
            rst_tx <= 1'b0;
        end else begin
            rst_tx <= rst_tx;
        end
    end

    // Time management
    TIME_FORMAT time_in [0:1];
    (* mark_debug = "true" *) TIME_FORMAT time_curr;
    TIME_FORMAT time_next;
    wire time_eq_tx, time_eq_rx;

    // Representation of TX and RX data signals
    (* mark_debug = "true" *) wire out_tx;
    (* mark_debug = "true" *) FILTER_IN_FORMAT sig_tx;
    (* mark_debug = "true" *) FILTER_OUT_FORMAT sig_rx;
    
    // Create TX clock
    const_clock #(.INC(TX_INC)) tx_clk_i(.clk(clk_sys),
                                         .rst(rst_sys),
                                         .time_next(time_next),
                                         .time_clock(time_in[0]),
                                         .cke_out(cke_tx),
                                         .time_eq(time_eq_tx));

    // Create random data generator
    prbs prbs_i(.out(out_tx),
                .clk(clk_tx),
                .rst(rst_tx));

    // Drive data into channel
    tx_ffe tx_ffe_i(.in(out_tx),
                    .out(sig_tx),
                    .tx_setting(tx_setting),
                    .clk(clk_tx),
                    .rst(rst_tx));

    // Filter data stream according to channel + CTLE dynamics
    filter filter_i(.in(sig_tx),
                    .time_eq_in(time_eq_tx),
                    .out(sig_rx),
                    .time_next(time_next),
                    .rx_setting(rx_setting),
                    .clk(clk_sys),
                    .rst(rst_sys));

    // Create RX clock
    const_clock #(.N(2), 
                  .INC(RX_INC)) rx_clk_i(.time_next(time_next),
                                         .time_clock(time_in[1]),
                                         .cke_out({cke_rx_p, cke_rx_n}),
                                         .time_eq(time_eq_rx),
                                         .clk(clk_sys),
                                         .rst(rst_sys));

    // Create time manager
    time_manager #(.N(2)) tm(.time_in(time_in),
                             .time_next(time_next),
                             .time_curr(time_curr),
                             .clk(clk_sys),
                             .rst(rst_sys));

    // Monitor time
    (* mark_debug = "true" *) reg sim_done_reg;
    assign sim_done = sim_done_reg;
    always @(posedge clk_sys) begin
        if (rst == 1'b1) begin
            sim_done_reg <= 1'b0;
        end else if (time_curr >= TIME_STOP) begin
            sim_done_reg <= 1'b1;
        end else begin
            sim_done_reg <= sim_done;
        end
    end

    // conditional instantiation of ADCs
    generate
        if (USE_ADC == 1) begin
            // TX signal monitor
            adc #(.name("tx"),
                  .sig_bits(FILTER_IN_WIDTH), 
                  .sig_point(FILTER_IN_POINT)) adc_tx(.clk(clk_tx),
                                                      .time_curr(time_curr),
                                                      .sig(sig_tx));
                                                    
            // RX rising edge signal monitor
            adc #(.name("rxp"),
                  .sig_bits(FILTER_OUT_WIDTH),
                  .sig_point(FILTER_OUT_POINT)) adc_rxp(.clk(clk_rx_p),
                                                        .time_curr(time_curr),
                                                        .sig(sig_rx));
          
            // RX falling edge signal monitor                              
            adc #(.name("rxn"),
                  .sig_bits(FILTER_OUT_WIDTH),
                  .sig_point(FILTER_OUT_POINT)) adc_rxn(.clk(clk_rx_n),
                                                        .time_curr(time_curr),
                                                        .sig(sig_rx));
        end
    endgenerate
endmodule
