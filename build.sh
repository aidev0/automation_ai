#!/bin/bash

# Exit on error
set -e

echo "Starting build process..."

# Clean Python cache files
echo "Cleaning Python cache files..."
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -r {} +

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run setup_venv.sh first"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Verify activation
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Error: Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip and install/upgrade dependencies
echo "Upgrading pip and dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run tests
echo "Running tests..."
python -m pytest -v

# Deactivate virtual environment
deactivate

echo "Build completed successfully!" 