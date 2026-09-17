cmake_minimum_required(VERSION 3.20)
project(orion_native CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Use modern FindPython with pybind11
set(PYBIND11_FINDPYTHON ON)
find_package(Python 3.11 REQUIRED COMPONENTS Interpreter Development.Module)

# Auto-detect pybind11 from current Python environment if not already set
if(NOT pybind11_DIR)
    execute_process(
        COMMAND "${Python_EXECUTABLE}" -m pybind11 --cmakedir
        OUTPUT_VARIABLE PYBIND11_DIR_DETECTED
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
    )
    if(PYBIND11_DIR_DETECTED)
        set(pybind11_DIR "${PYBIND11_DIR_DETECTED}" CACHE PATH "Path to pybind11 cmake dir" FORCE)
    endif()
endif()

find_package(pybind11 CONFIG REQUIRED)

# Optional OpenCV support
find_package(OpenCV QUIET)
if(OpenCV_FOUND)
    message(STATUS "OpenCV found: ${OpenCV_VERSION}")
    add_compile_definitions(USE_OPENCV)
else()
    message(STATUS "OpenCV not found; building C++ core with native fallback engines.")
endif()

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
if(OpenCV_FOUND)
    include_directories(${OpenCV_INCLUDE_DIRS})
endif()

# Core static library
set(ORION_CORE_SRCS
    src/core/frame_buffer.cpp
    src/camera/camera_engine.cpp
    src/vision/video_processor.cpp
    src/tracking/tracker.cpp
    src/video/video_encoder.cpp
    src/streaming/stream_engine.cpp
)

add_library(orion_core STATIC ${ORION_CORE_SRCS})
target_include_directories(orion_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
if(OpenCV_FOUND)
    target_link_libraries(orion_core PUBLIC ${OpenCV_LIBS})
endif()

# Pybind11 extension module
pybind11_add_module(orion_native bindings/pybind_module.cpp)
target_link_libraries(orion_native PRIVATE orion_core)

# Set output directory to repo root so 'import orion_native' works directly in Python
set_target_properties(orion_native PROPERTIES
    PREFIX ""
    OUTPUT_NAME "orion_native"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/.."
)
