ROOTDIR         := {{ROOTDIR}}
EXECUTABLE      := runner
{% if prefs['devices.genn.cpu_only'] %}
SOURCES := runner_cpu_only.cc {% for source in source_files %} {{source}} {% endfor %}

{% else %}
SOURCES         := runner.cu {% for source in source_files %} {{source}} {% endfor %}

{% endif %}


INCLUDE_FLAGS   := -I.
OPTIMIZATIONFLAGS := {{prefs['devices.genn.unix_compiler_flags']}}

include $(GENN_PATH)/userproject/include/makefile_common_gnu.mk

