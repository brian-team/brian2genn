#!/bin/sh

# Compile GeNN libraries
(GENN_PATH="$(pwd)/genn"; cd genn/lib; make "$GENN_PATH/lib/lib/libgenn.a" GENN_PATH="$GENN_PATH")
(GENN_PATH="$(pwd)/genn"; cd genn/lib; make "$GENN_PATH/lib/lib/libgenn_CPU_ONLY.a" GENN_PATH="$GENN_PATH" CPU_ONLY=1)

# Install Python package with GeNN libraries
python setup.py install --single-version-externally-managed --record record.txt --with-genn
