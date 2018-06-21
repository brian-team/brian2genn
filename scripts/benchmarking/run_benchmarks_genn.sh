#!/bin/bash -e

for spikemon in "true"; do
   for threads in 0 -1; do
       for scaling in 0.05 0.1 0.25 0.5 1 2 4 8 16 32; do
	   time=1;
               for repeat in 1 2 3; do
                   echo Repeat $repeat
                   python $1 $scaling genn $threads $spikemon true $time
                   rm -r GeNNworkspace
	       done
       done
   done
done
		   
# The really long runs (don't run with GeNN CPU-only, etc.)
for spikemon in "true"; do
    for scaling in 64 128 256; do
	time=1;
	    for repeat in 1 2; do
		echo Repeat $repeat
                python $1 $scaling genn 0 $spikemon true $time
                rm -r GeNNworkspace
	    done
    done
done
