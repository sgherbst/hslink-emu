import time_package::*;
import rx_package::*;

module top;
    localparam longint max_code = (longint'(1)<<longint'(DCO_CODE_WIDTH)) - longint'(1);

    integer f;
    initial begin
        f = $fopen("dco_pwl_emu.txt", "w");
    end

    reg clk = 1'b0;
    reg rst = 1'b0;

    DCO_CODE_FORMAT code;
    DCO_PERIOD_FORMAT period;

    // PWL instantiation
    pwl #(
        // note: setting_width=0 to indicate there
        // are not multiple settings
        .setting_width(0),
        
        // note: address offset is zero because 
        // DCO codes start at 0 and go up to (1<<DCO_CODE_WIDTH)-1
        .addr_offset(0),

        // handle bias value, which is specified as a parameter rather
        // than as a ROM
        .bias_width(RX_DCO_BIAS_WIDTH),
        .bias_val(RX_DCO_BIAS_VAL),

        .segment_rom_name(RX_DCO_ROM_NAME),
        .in_width(DCO_CODE_WIDTH),
        .in_point(DCO_CODE_POINT),
        .addr_width(RX_DCO_ADDR_WIDTH),
        .segment_width(RX_DCO_SEGMENT_WIDTH),
        .offset_width(RX_DCO_OFFSET_WIDTH),
        .slope_width(RX_DCO_SLOPE_WIDTH),
        .slope_point(RX_DCO_SLOPE_POINT),
        .out_width(DCO_PERIOD_WIDTH),
        .out_point(DCO_PERIOD_POINT)
    ) dco_pwl (
        .in(code), 
        .out(period),
        .clk(clk),
        .rst(rst),
        // setting input is not used, but SystemVerilog
        // does not provide a mechanism to indicate an
        // unused port.  to a bogus warning, the port
        // is driven with a signal of the appropriate
        // width [-1:0] => 2 bits wide
        .setting(2'b00)
    );

    initial begin
        // reset
        rst = 1'b1;
        #5;
        clk = 1'b1;
        #5;
        rst = 1'b0;
        #5;
        clk = 1'b0;

        // loop over codes
        for (longint i=0; i <= max_code; i = i+1) begin
            code = i;
            #5;
            clk = 1'b1;
            #5
            $fwrite(f, "%d,\t%0.9e\n", code, real'(period)/(real'(2)**real'(DCO_PERIOD_POINT)));
            clk = 1'b0;
        end

        $finish;
    end
endmodule
