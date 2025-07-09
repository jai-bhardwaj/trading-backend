#!/usr/bin/env python3
"""
Quick Compilation Check - Like C++/Java compilation
Only checks for critical errors that prevent the project from running
"""

import subprocess
import sys
from pathlib import Path

def check_syntax():
    """Check Python syntax for all .py files"""
    print("🔍 SYNTAX CHECK (Critical)")
    print("-" * 40)
    
    python_files = list(Path(".").rglob("*.py"))
    errors = []
    
    for file_path in python_files:
        if "venv" in str(file_path) or "__pycache__" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r') as f:
                compile(f.read(), str(file_path), 'exec')
        except SyntaxError as e:
            errors.append(f"❌ {file_path}: {e}")
        except Exception as e:
            errors.append(f"❌ {file_path}: {e}")
    
    if errors:
        print(f"❌ COMPILATION FAILED: {len(errors)} syntax errors")
        for error in errors[:5]:  # Show first 5 errors
            print(error)
        return False
    else:
        print(f"✅ SYNTAX OK: {len(python_files)} files compiled successfully")
        return True

def check_imports():
    """Check if critical imports work"""
    print("\n🔍 IMPORT CHECK (Critical)")
    print("-" * 40)
    
    critical_modules = [
        "api.main",
        "models_clean",
        "shared.database"
    ]
    
    for module in critical_modules:
        try:
            subprocess.run([sys.executable, "-c", f"import {module}"], 
                         check=True, capture_output=True)
            print(f"✅ {module}")
        except subprocess.CalledProcessError:
            print(f"❌ {module}: Import failed")
            return False
    
    return True

def check_fastapi():
    """Check if FastAPI app loads"""
    print("\n🔍 FASTAPI CHECK (Critical)")
    print("-" * 40)
    
    try:
        subprocess.run([sys.executable, "-c", 
                       "from api.main import app; print('FastAPI OK')"], 
                      check=True, capture_output=True)
        print("✅ FastAPI app loads successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ FastAPI app failed to load")
        return False

def main():
    """Run critical compilation checks only"""
    print("⚡ QUICK COMPILATION CHECK")
    print("=" * 50)
    print("Checking only CRITICAL errors (like C++/Java compilation)")
    print("=" * 50)
    
    checks = [
        ("Syntax Check", check_syntax),
        ("Import Check", check_imports),
        ("FastAPI Check", check_fastapi)
    ]
    
    all_passed = True
    for name, check_func in checks:
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 COMPILATION SUCCESSFUL!")
        print("Your project compiles and can run without critical errors.")
        print("(Style/quality issues may exist but don't prevent execution)")
        sys.exit(0)
    else:
        print("💥 COMPILATION FAILED!")
        print("Fix the critical errors above before running the project.")
        sys.exit(1)

if __name__ == "__main__":
    main() 