#!/bin/bash -e

if [ "$1" = "COBAHH_MON.py" ]; then 
    mon=0.1;
else
    mon="";
fi

for spikemon in "true"; do
   for threads in 1 2 4 8 16; do
       for scaling in  0.05 0.1 0.25 0.5 1 2 4 8 16 32; do
	   time=1;
               for repeat in 1 2 3 4 5; do
                   echo Repeat $repeat
                   python $1 $scaling cpp_standalone $threads $spikemon true $time $mon
                   rm -r output
	       done
       done
   done
done
		   
# The really long runs (don't run with low # of threads, etc.)

if [ "$1" = "Mbody_example.py" ]; then 
    for spikemon in "true"; do
	for threads in 8 16; do
	    for scaling in 64 128 256 512; do
		time=1;
		for repeat in 1 2 3; do
		    echo Repeat $repeat
		    python $1 $scaling cpp_standalone $threads $spikemon true $time $mon
		    rm -r output
		done
	    done
	done
    done
fi
		    
