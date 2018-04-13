import signal_package::*;
import time_package::*;
import tx_package::*;

module adc_gen(
    input wire clk_tx,
    input wire clk_rx_p,
    input wire clk_rx_n,
    input TIME_FORMAT time_curr,
    input FILTER_IN_FORMAT filter_in,
    input FILTER_OUT_FORMAT filter_out
);

    // TX signal monitor
    adc #(
        .name("tx"),
        .sig_bits(FILTER_IN_WIDTH), 
        .sig_point(FILTER_IN_POINT)
    ) adc_tx (
        .clk(clk_tx),
        .time_curr(time_curr),
        .sig(filter_in)
    );
                                            
    // RX rising edge signal monitor
    adc #(
        .name("rxp"),
        .sig_bits(FILTER_OUT_WIDTH), 
        .sig_point(FILTER_OUT_POINT)
    ) adc_rx_p (
        .clk(clk_rx_p),
        .time_curr(time_curr),
        .sig(filter_out)
    );
    
    // RX falling edge signal monitor                              
    adc #(
        .name("rxn"),
        .sig_bits(FILTER_OUT_WIDTH), 
        .sig_point(FILTER_OUT_POINT)
    ) adc_rx_n (
        .clk(clk_rx_n),
        .time_curr(time_curr),
        .sig(filter_out)
    );

endmodule
