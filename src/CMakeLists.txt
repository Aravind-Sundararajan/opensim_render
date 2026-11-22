# Set SWIG flags
set(CMAKE_SWIG_FLAGS "-c++")

# Set source files for SWIG module
set(SWIG_SOURCE_FILE "${CMAKE_CURRENT_SOURCE_DIR}/../osim_render.i")
set_source_files_properties(${SWIG_SOURCE_FILE} PROPERTIES CPLUSPLUS ON)

# Add include directory for SWIG
include_directories(${CMAKE_CURRENT_SOURCE_DIR})

# Add the SWIG module
swig_add_library(osim_render
    TYPE SHARED
    LANGUAGE python
    SOURCES ${SWIG_SOURCE_FILE} mesh_loader.cpp loader_impl.cpp
)

# Link Python libraries
target_link_libraries(osim_render PRIVATE Python3::Python)

# Include directories for headers
target_include_directories(osim_render PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(osim_render PRIVATE ${Python3_INCLUDE_DIRS})

# Emit the extension straight into the Python package so `from . import
# _osim_render` resolves without a post-build copy. On Windows the .pyd is a
# RUNTIME artifact; elsewhere the .so is a LIBRARY artifact, so both are set.
set(OSIM_RENDER_PACKAGE_DIR "${CMAKE_SOURCE_DIR}/osim_render")

set_target_properties(osim_render PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${OSIM_RENDER_PACKAGE_DIR}"
    LIBRARY_OUTPUT_DIRECTORY "${OSIM_RENDER_PACKAGE_DIR}"
)

# Multi-config generators (Visual Studio) otherwise append Release/ or Debug/.
foreach(output_config IN LISTS CMAKE_CONFIGURATION_TYPES)
    string(TOUPPER "${output_config}" output_config_upper)
    set_target_properties(osim_render PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY_${output_config_upper} "${OSIM_RENDER_PACKAGE_DIR}"
        LIBRARY_OUTPUT_DIRECTORY_${output_config_upper} "${OSIM_RENDER_PACKAGE_DIR}"
    )
endforeach()

# Windows-specific settings
if(WIN32)
    # On Windows, Python extension modules must use .pyd extension
    set_target_properties(osim_render PROPERTIES SUFFIX ".pyd")

    # Ensure proper Python module naming
    set_target_properties(osim_render PROPERTIES PREFIX "_")
endif()

# SWIG also regenerates a Python proxy next to the build tree. The checked-in
# copy at osim_render/_osim_render_native.py is hand-formatted and annotated;
# it must not be overwritten by the generated file.

# Print configuration
message(STATUS "SWIG module osim_render configured")
message(STATUS "  Source: ${SWIG_SOURCE_FILE}")
message(STATUS "  Implementation: mesh_loader.cpp")
message(STATUS "  Output directory: ${OSIM_RENDER_PACKAGE_DIR}")
