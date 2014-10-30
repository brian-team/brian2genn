ROOTDIR         := {{ROOTDIR}}
EXECUTABLE      := runner
SOURCES         := runner.cu {% for source in source_files %} {{source}} {% endfor %}

INCLUDE_FLAGS   := -I.
LINK_FLAGS      := 
CCFLAGS         := 
NVCCFLAGS       := 

include $(GeNNPATH)/userproject/include/makefile_common_gnu.mk

