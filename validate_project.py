#!/usr/bin/env python3
"""
Comprehensive Project Validation Script
Similar to compilation in C++/Java - checks for errors across the entire project
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n🔍 {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {description}: PASSED")
            if result.stdout.strip():
                print(result.stdout)
        else:
            print(f"❌ {description}: FAILED")
            if result.stderr.strip():
                print(result.stderr)
            if result.stdout.strip():
                print(result.stdout)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False

def check_python_syntax():
    """Check Python syntax for all .py files"""
    print("\n🔍 Checking Python Syntax (like compilation)")
    print("=" * 60)
    
    python_files = list(Path(".").rglob("*.py"))
    errors = []
    
    for file_path in python_files:
        if "venv" in str(file_path) or "__pycache__" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r') as f:
                compile(f.read(), str(file_path), 'exec')
            print(f"✅ {file_path}")
        except SyntaxError as e:
            errors.append(f"❌ {file_path}: {e}")
            print(f"❌ {file_path}: {e}")
        except Exception as e:
            errors.append(f"❌ {file_path}: {e}")
            print(f"❌ {file_path}: {e}")
    
    if errors:
        print(f"\n❌ Syntax Check: FAILED ({len(errors)} errors)")
        return False
    else:
        print(f"\n✅ Syntax Check: PASSED (checked {len(python_files)} files)")
        return True

def check_imports():
    """Check if all imports can be resolved"""
    print("\n🔍 Checking Import Resolution")
    print("=" * 60)
    
    # Try importing main modules
    modules_to_test = [
        "api.main",
        "api.services.trading_service",
        "models_clean",
        "shared.database",
        "order.manager",
        "strategy.engine"
    ]
    
    errors = []
    for module in modules_to_test:
        try:
            subprocess.run([sys.executable, "-c", f"import {module}"], 
                         check=True, capture_output=True)
            print(f"✅ {module}")
        except subprocess.CalledProcessError as e:
            errors.append(f"❌ {module}: Import failed")
            print(f"❌ {module}: Import failed")
    
    if errors:
        print(f"\n❌ Import Check: FAILED ({len(errors)} errors)")
        return False
    else:
        print(f"\n✅ Import Check: PASSED")
        return True

def main():
    """Run all validation checks"""
    print("🧪 COMPREHENSIVE PROJECT VALIDATION")
    print("=" * 60)
    print("This is equivalent to 'compiling' your Python project")
    print("to check for errors, missing imports, and other issues.")
    print("=" * 60)
    
    results = []
    
    # 1. Python Syntax Check (like compilation)
    results.append(check_python_syntax())
    
    # 2. Import Resolution Check
    results.append(check_imports())
    
    # 3. Type Checking with MyPy
    results.append(run_command(
        "mypy api/ --ignore-missing-imports --no-strict-optional",
        "Type Checking (MyPy)"
    ))
    
    # 4. Code Style Check
    results.append(run_command(
        "flake8 api/ models_clean.py --max-line-length=100 --ignore=E501,W503",
        "Code Style Check (Flake8)"
    ))
    
    # 5. Static Analysis
    results.append(run_command(
        "pylint api/ models_clean.py --disable=C0114,C0115,C0116,R0903,R0913,W0613",
        "Static Analysis (Pylint)"
    ))
    
    # 6. Security Check
    results.append(run_command(
        "bandit -r api/ -f txt",
        "Security Analysis (Bandit)"
    ))
    
    # 7. Dependency Vulnerability Check
    results.append(run_command(
        "safety check",
        "Dependency Security Check (Safety)"
    ))
    
    # 8. FastAPI App Validation
    results.append(run_command(
        "python -c \"from api.main import app; print('✅ FastAPI app loads successfully')\"",
        "FastAPI Application Validation"
    ))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    checks = [
        "Python Syntax Check",
        "Import Resolution", 
        "Type Checking",
        "Code Style Check",
        "Static Analysis",
        "Security Analysis",
        "Dependency Security",
        "FastAPI Validation"
    ]
    
    for i, (check, result) in enumerate(zip(checks, results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{i+1}. {check}: {status}")
    
    print("=" * 60)
    
    if passed == total:
        print("🎉 ALL CHECKS PASSED - PROJECT IS VALID!")
        print("Your project compiles successfully (equivalent)")
        sys.exit(0)
    else:
        print(f"⚠️  {total - passed} CHECKS FAILED - ISSUES FOUND")
        print("Fix the issues above and run again")
        sys.exit(1)

if __name__ == "__main__":
    main() 