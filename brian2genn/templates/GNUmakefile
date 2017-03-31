ROOTDIR         := {{ROOTDIR}}
EXECUTABLE      := main
{% if not use_GPU %}
CPU_ONLY	    = 1
{% endif %}
SOURCES         := main.cpp {% for source in source_files %} {{source}} {% endfor %} brianlib/randomkit/randomkit.cc

INCLUDE_FLAGS   := -I. -Ibrianlib/randomkit -Lbrianlib/randomkit
OPTIMIZATIONFLAGS := {{compiler_flags}}
NVCC_OPTIMIZATIONFLAGS := {{nvcc_compiler_flags}}
SIM_CODE := {{model_name}}_CODE

include $(GENN_PATH)/userproject/include/makefile_common_gnu.mk
