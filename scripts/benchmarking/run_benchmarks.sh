#!/bin/bash -e

for spikemon in "true" "false"; do
   for threads in -1 0; do
        for scaling in 1 2 5 10 20 50; do
            for repeat in 1 2; do
                echo Repeat $repeat
                python Mbody_example.py $scaling genn $threads $spikemon true
                rm -r GeNNworkspace
                echo Empty run
                python Mbody_example.py $scaling genn $threads $spikemon false
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
                python Mbody_example.py $scaling cpp_standalone $threads $spikemon true
                rm -r output
                echo Empty run
                python Mbody_example.py $scaling cpp_standalone $threads $spikemon false
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
            python Mbody_example.py $scaling genn 0 $spikemon true
            rm -r GeNNworkspace
            echo Empty run
            python Mbody_example.py $scaling genn 0 $spikemon false
            rm -r GeNNworkspace
        done
    done
done

for spikemon in "true" "false"; do
    for threads in 4 8; do
        for scaling in 100 200; do
            for repeat in 1 2; do
                echo Repeat $repeat
                python Mbody_example.py $scaling cpp_standalone $threads $spikemon true
                rm -r output
                echo Empty run
                python Mbody_example.py $scaling cpp_standalone $threads $spikemon false
                rm -r output
            done
        done
    done
done
