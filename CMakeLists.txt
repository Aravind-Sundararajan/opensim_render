cmake_minimum_required(VERSION 3.18)
project(osim_render)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Single-config generators (Ninja, Unix Makefiles) default to an empty, and
# therefore unoptimized, build type. Multi-config generators pick per --config.
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# The extension must be built against the same interpreter that imports it.
# Left to itself, find_package(Python3) picks the first Python on PATH, which
# is often a system or Poetry-venv install with a different ABI than the conda
# environment the app runs in; the resulting module fails to import.
# Pass -DPython3_EXECUTABLE=... to override.
if(NOT DEFINED Python3_EXECUTABLE AND DEFINED ENV{CONDA_PREFIX})
    if(WIN32)
        set(Python3_EXECUTABLE "$ENV{CONDA_PREFIX}/python.exe")
    else()
        set(Python3_EXECUTABLE "$ENV{CONDA_PREFIX}/bin/python")
    endif()
endif()

# Find Python3 with development headers
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

if(NOT Python3_VERSION MATCHES "^3\\.(11|12)")
    message(WARNING
        "Building against Python ${Python3_VERSION} (${Python3_EXECUTABLE}), but "
        "osim_render requires >=3.11,<3.13. The extension will not be importable "
        "by the application. Pass -DPython3_EXECUTABLE=<conda env python>.")
endif()

# Find SWIG
find_package(SWIG 4.0 REQUIRED)
include(${SWIG_USE_FILE})

# Include subdirectory with mesh loader sources
add_subdirectory(src)

# Print summary
message(STATUS "Python3 executable: ${Python3_EXECUTABLE}")
message(STATUS "Python3 include dirs: ${Python3_INCLUDE_DIRS}")
message(STATUS "Python3 libraries: ${Python3_LIBRARIES}")
message(STATUS "SWIG executable: ${SWIG_EXECUTABLE}")
