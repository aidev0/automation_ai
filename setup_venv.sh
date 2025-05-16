#!/bin/bash

# Exit on error
set -e

echo "Removing existing virtual environment..."
rm -rf ./venv


echo "Setting up Python virtual environment..."


# Check for Python installation
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3 using one of these methods:"
    echo "1. Using Homebrew (recommended):"
    echo "   brew install python@3.13"
    echo "2. Download from python.org:"
    echo "   https://www.python.org/downloads/"
    echo ""
    echo "After installation, try running this script again."
    exit 1
fi

# Get Python version
PYTHON_VERSION=$(python3 --version 2>&1)
echo "Found $PYTHON_VERSION"

# Verify Python version is 3.13
if [[ ! $PYTHON_VERSION =~ "Python 3.13" ]]; then
    echo "Warning: Expected Python 3.13, but found $PYTHON_VERSION"
    echo "Please ensure Python 3.13 is installed and set as default"
    exit 1
fi

# Check if venv module is available
if ! python3 -c "import venv" &> /dev/null; then
    echo "Error: Python venv module is not installed"
    echo "Please install it using: python3 -m pip install virtualenv"
    exit 1
fi

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# Create virtual environment
echo "Creating new virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Verify activation
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Error: Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        exit 1
    fi
else
    echo "Error: requirements.txt not found"
    exit 1
fi

# Install pytest for testing
pip install pytest

echo "Virtual environment setup complete!"
echo "To activate the virtual environment, run: source venv/bin/activate"
echo "To deactivate the virtual environment, run: deactivate" 