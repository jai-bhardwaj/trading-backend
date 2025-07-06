#!/usr/bin/env python3
"""
Test runner for the trading backend test suite.
"""
import sys
import os
import argparse
import subprocess
import asyncio
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Command timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def run_unit_tests():
    """Run unit tests."""
    cmd = [
        "python3", "-m", "pytest", 
        "tests/unit/", 
        "-v", 
        "--tb=short",
        "--durations=10"
    ]
    return run_command(cmd, "Unit Tests")

def run_integration_tests():
    """Run integration tests."""
    cmd = [
        "python3", "-m", "pytest", 
        "tests/integration/", 
        "-v", 
        "--tb=short",
        "--durations=10"
    ]
    return run_command(cmd, "Integration Tests")

def run_security_tests():
    """Run security tests."""
    cmd = [
        "python3", "-m", "pytest", 
        "tests/security/", 
        "-v", 
        "--tb=short",
        "--durations=10"
    ]
    return run_command(cmd, "Security Tests")

def run_performance_tests():
    """Run performance tests."""
    cmd = [
        "python3", "-m", "pytest", 
        "tests/performance/", 
        "-v", 
        "--tb=short",
        "--durations=10"
    ]
    return run_command(cmd, "Performance Tests")

def run_all_tests():
    """Run all tests."""
    cmd = [
        "python3", "-m", "pytest", 
        "tests/", 
        "-v", 
        "--tb=short",
        "--durations=10"
    ]
    return run_command(cmd, "All Tests")

def run_tests_with_coverage():
    """Run tests with coverage report."""
    cmd = [
        "python3", "-m", "pytest", 
        "tests/", 
        "-v", 
        "--tb=short",
        "--cov=services",
        "--cov=shared",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--durations=10"
    ]
    return run_command(cmd, "Tests with Coverage")

def run_specific_test(test_path):
    """Run a specific test file or test."""
    cmd = [
        "python3", "-m", "pytest", 
        test_path, 
        "-v", 
        "--tb=short",
        "--durations=10"
    ]
    return run_command(cmd, f"Specific Test: {test_path}")

def run_tests_with_markers(marker):
    """Run tests with specific markers."""
    cmd = [
        "python3", "-m", "pytest", 
        "tests/", 
        "-v", 
        "--tb=short",
        f"-m", marker,
        "--durations=10"
    ]
    return run_command(cmd, f"Tests with marker: {marker}")

def check_redis_connection():
    """Check if Redis is running."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("Please start Redis server before running tests")
        return False

def setup_test_environment():
    """Setup test environment."""
    print("Setting up test environment...")
    
    # Check Redis
    if not check_redis_connection():
        return False
    
    # Set environment variables
    os.environ["TESTING"] = "true"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["MOCK_EXTERNAL_APIS"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    print("✅ Test environment setup complete")
    return True

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Trading Backend Test Runner")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "security", "performance", "all"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--test", 
        type=str,
        help="Run a specific test file or test"
    )
    parser.add_argument(
        "--marker", 
        type=str,
        help="Run tests with specific marker"
    )
    parser.add_argument(
        "--setup-only", 
        action="store_true",
        help="Only setup test environment"
    )
    
    args = parser.parse_args()
    
    print("🚀 Trading Backend Test Runner")
    print("=" * 50)
    
    # Setup environment
    if not setup_test_environment():
        sys.exit(1)
    
    if args.setup_only:
        print("✅ Environment setup complete")
        return
    
    # Run tests based on arguments
    success = False
    
    if args.test:
        success = run_specific_test(args.test)
    elif args.marker:
        success = run_tests_with_markers(args.marker)
    elif args.coverage:
        success = run_tests_with_coverage()
    elif args.type == "unit":
        success = run_unit_tests()
    elif args.type == "integration":
        success = run_integration_tests()
    elif args.type == "security":
        success = run_security_tests()
    elif args.type == "performance":
        success = run_performance_tests()
    else:  # all
        success = run_all_tests()
    
    # Print summary
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 