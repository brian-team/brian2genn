ROOTDIR         := {{ROOTDIR}}
EXECUTABLE      := main
{% if prefs['devices.genn.cpu_only'] %}
CPU_ONLY	    = 1
{% else %}
CPU_ONLY	    = 0
{% endif %}
SOURCES         := main.cpp {% for source in source_files %} {{source}} {% endfor %} brianlib/randomkit/randomkit.c

INCLUDE_FLAGS   := -I. -Ibrianlib/randomkit -Lbrianlib/randomkit
OPTIMIZATIONFLAGS := {{prefs['devices.genn.unix_compiler_flags']}}

include $(GENN_PATH)/userproject/include/makefile_common_gnu.mk

