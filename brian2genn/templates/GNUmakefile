ROOTDIR         := {{ROOTDIR}}
EXECUTABLE      := main
SOURCES         := main.cc {% for source in source_files %} {{source}} {% endfor %}

INCLUDE_FLAGS   := -I.
OPTIMIZATIONFLAGS := {{prefs['devices.genn.unix_compiler_flags']}}

include $(GENN_PATH)/userproject/include/makefile_common_gnu.mk

