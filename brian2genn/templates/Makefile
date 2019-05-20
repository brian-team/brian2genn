GENERATED_CODE_DIR	:=magicnetwork_model_CODE
CXXFLAGS 		+=-std=c++11 -Wno-write-strings -I. -Ibrianlib/randomkit

.PHONY: all clean generated_code

all: main

main: main.cpp {% for source in source_files %} {{source}} {% endfor %} brianlib/randomkit/randomkit.cc generated_code
	$(CXX) $(CXXFLAGS)  main.cpp {% for source in source_files %} {{source}} {% endfor %} brianlib/randomkit/randomkit.cc -o main -L$(GENERATED_CODE_DIR) -lrunner -Wl,-rpath $(GENERATED_CODE_DIR)

generated_code:
	$(MAKE) -C $(GENERATED_CODE_DIR)
