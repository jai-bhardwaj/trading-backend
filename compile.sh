#!/bin/bash
"""
Python Project Compilation Script
Usage: ./compile.sh [--full]
"""

set -e

echo "🔨 Compiling Trading Backend Project..."
echo ""

# Activate virtual environment
source venv/bin/activate

if [ "$1" = "--full" ]; then
    echo "Running FULL validation (includes style checks)..."
    python validate_project.py
else
    echo "Running QUICK compilation check (critical errors only)..."
    python quick_compile_check.py
fi

echo ""
echo "✅ Use './compile.sh --full' for comprehensive validation"
echo "✅ Use './compile.sh' for quick compilation check" 