# Compile GeNN libraries
set GENN_PATH=%CD%/genn
nmake /f genn/lib/WINmakefile %GENN_PATH%/lib/lib/genn.lib "GENN_PATH=%GENN_PATH%"
nmake /f genn/lib/WINmakefile %GENN_PATH%/lib/lib/genn_CPU_ONLY.lib "GENN_PATH=%GENN_PATH%" CPU_ONLY=1

# Install Python package with GeNN libraries
python setup.py install --single-version-externally-managed --record record.txt --with-genn
