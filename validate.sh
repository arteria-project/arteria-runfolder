#!/bin/bash

echo "Unit tests..."
nosetests ./runfolder_tests/unit

echo "Integration tests..."
python ./runfolder_tests/run_integration_tests.py
