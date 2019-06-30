module top import iotype::*; (
	input voltage_t x,
	output voltage_t y
);

	buff buff_i(x, y);

endmodule
