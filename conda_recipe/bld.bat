REM The following path assumes an installation of MS Visual Studio 2015
call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" amd64
REM Compile GeNN libraries
set GENN_PATH=%CD%\genn
nmake /f genn\lib\WINmakefile %GENN_PATH%\lib\lib\genn.lib "GENN_PATH=%GENN_PATH%"
nmake /f genn\lib\WINmakefile %GENN_PATH%\lib\lib\genn_CPU_ONLY.lib "GENN_PATH=%GENN_PATH%" CPU_ONLY=1

REM Install Python package with GeNN libraries
python setup.py install --single-version-externally-managed --record record.txt --with-genn
