#!/bin/bash
# Script to run ZanSoc CLI with virtual environment

# Change to CLI directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run the CLI with any passed arguments
zansoc "$@"