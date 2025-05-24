#!/bin/bash

echo "🔧 Checking Python version..."
PYTHON_BIN=$(command -v python3 || command -v python)
if [ -z "$PYTHON_BIN" ]; then
  echo "❌ Python 3 not found. Please install it and retry."
  exit 1
fi

echo "🐍 Creating virtual environment..."
$PYTHON_BIN -m venv venv

echo "✅ Activating virtual environment..."
# Platform-specific activation
if [[ "$OSTYPE" == "darwin"* || "$OSTYPE" == "linux-gnu"* ]]; then
  source venv/bin/activate
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  source venv/Scripts/activate
else
  echo "⚠️ Unknown OS. Activate manually using 'source venv/bin/activate'"
fi

echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Environment ready."
echo "👉 Run your agent with:"
echo "source venv/bin/activate && python main.py"
