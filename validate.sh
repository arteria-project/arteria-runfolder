#!/bin/bash

echo "Unit tests..."
nosetests ./tests/unit

echo "Integration tests..."
./tests/run_integration_tests.py
