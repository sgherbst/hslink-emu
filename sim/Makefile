TOP := top

all: run

obj_dir/done.txt: opt.f *.*v sim.cpp
	verilator --cc -Wall --exe sim.cpp -F opt.f --top-module $(TOP)
	make -j -C obj_dir -f V$(TOP).mk V$(TOP)
	touch obj_dir/done.txt

run: obj_dir/done.txt
	obj_dir/V$(TOP)

clean:
	rm -rf obj_dir
