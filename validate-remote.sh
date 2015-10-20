#!/bin/bash

echo "Integration tests..."
python ./runfolder_tests/run_integration_tests.py http://testarteria1:10800/api/1.0 /data/testarteria1/runfolders

