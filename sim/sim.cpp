#include "Vtop.h"
#include "verilated.h"

int main(int argc, char** argv, char** env) {
	Verilated::commandArgs(argc, argv);
	
	Vtop* top = new Vtop;
	
	for (double x=0.0; x<10.0; x++) {
		top->x = x;
		top->eval();
		printf("x=%0.3f, y=%0.3f\n", top->x, top->y);
	}
	
	delete top;
	
	exit(0);
}
