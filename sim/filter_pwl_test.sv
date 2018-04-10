import time_package::*;
import filter_package::*;

module top;
    localparam k=`FILTER_PWL_INDEX;

    localparam longint max_time = longint'(1)<<(longint'(FILTER_ADDR_WIDTHS[k])+longint'(FILTER_SEGMENT_WIDTHS[k]));

    integer f;
    initial begin
        f = $fopen("filter_pwl_emu.txt", "w");
    end

    reg clk = 1'b0;

    DT_FORMAT t;
    FILTER_STEP_FORMAT v;

    wire [RX_SETTING_WIDTH-1:0] rx_setting = `RX_SETTING;

    // PWL instantiation
    pwl #(.segment_rom_name(FILTER_SEGMENT_ROM_PATHS[k]),
          .bias_rom_name(FILTER_BIAS_ROM_PATHS[k]),
          .bias_width(FILTER_BIAS_WIDTHS[k]),
          .n_settings(NUM_RX_SETTINGS),
          .setting_width(RX_SETTING_WIDTH),
          .in_width(DT_WIDTH),
          .in_point(DT_POINT),
          .addr_width(FILTER_ADDR_WIDTHS[k]),
          .addr_offset(FILTER_ADDR_OFFSETS[k]),
          .segment_width(FILTER_SEGMENT_WIDTHS[k]),
          .offset_width(FILTER_OFFSET_WIDTHS[k]),
          .slope_width(FILTER_SLOPE_WIDTHS[k]),
          .slope_point(FILTER_SLOPE_POINTS[k]),
          .out_width(FILTER_STEP_WIDTH),
          .out_point(FILTER_STEP_POINT)) pwl_k (.in(t), 
                                                .clk(clk),
                                                .out(v),
                                                .setting(rx_setting));

    initial begin
        for (longint i=0; i < max_time; i = i+1) begin
            t = i + longint'(FILTER_ADDR_OFFSETS[k]);
            #5;
            clk = 1'b1;
            #5
            $fwrite(f, "%0.9e,\t%0.9e\n", real'(t)/(real'(2)**real'(DT_POINT)), real'(v)/(real'(2)**real'(FILTER_STEP_POINT)));
            clk = 1'b0;
        end
        $finish;
    end
endmodule
