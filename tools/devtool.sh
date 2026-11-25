#!/usr/bin/env bash
cmake -S . -B build -DPython3_EXECUTABLE=python
cmake --build build --config Release
