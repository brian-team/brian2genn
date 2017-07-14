#!/bin/bash -e

for spikemon in "true" "false"; do
   for threads in 0 -1; do
        for scaling in 1 2 5 10 20 50; do
            for repeat in 1 2 3 4; do
                echo Repeat $repeat
                python $1 $scaling genn $threads $spikemon true
                rm -r GeNNworkspace
            done
        done
    done
done

for spikemon in "true" "false"; do
    for threads in 0 2 4 8; do
        for scaling in 1 2 5 10 20 50; do
            for repeat in 1 2; do
                echo Repeat $repeat
                python $1 $scaling cpp_standalone $threads $spikemon true
                rm -r output
            done
        done
    done
done

# The really long runs (don't run with GeNN CPU-only, etc.)
for spikemon in "true" "false"; do
    for scaling in 100 200; do
        for repeat in 1 2; do
            echo Repeat $repeat
            python $1 $scaling genn 0 $spikemon true
            rm -r GeNNworkspace
        done
    done
done

for spikemon in "true" "false"; do
    for threads in 4 8; do
        for scaling in 100 200; do
            for repeat in 1 2; do
                echo Repeat $repeat
                python $1 $scaling cpp_standalone $threads $spikemon true
                rm -r output
            done
        done
    done
done
