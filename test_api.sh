#!/bin/bash

set -e

API_URL="http://localhost:8000"
USERNAME="testuser_$(date +%s)"
EMAIL="test_$(date +%s)@example.com"
PASSWORD="testpass123"

echo "Testing API endpoints..."

# Test 1: Check if API is running
echo -e "\n1. Checking if API is running..."
if curl -s "$API_URL/docs" > /dev/null; then
    echo "✓ API is running"
else
    echo "✗ API is not running"
    exit 1
fi

# Test 2: Register user
echo -e "\n2. Registering user..."
curl -s -X POST "$API_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USERNAME\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
    -o register_response.json
cat register_response.json
echo

# Test 3: Login
echo -e "\n3. Logging in..."
curl -s -X POST "$API_URL/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$USERNAME&password=$PASSWORD" \
    -o login_response.json
cat login_response.json
echo

# Extract access token from login response
ACCESS_TOKEN=$(cat login_response.json | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -n "$ACCESS_TOKEN" ]; then
    echo "✓ Login successful"
else
    echo "✗ Login failed"
    exit 1
fi

# Test 4: Get user profile
echo -e "\n4. Getting user profile..."
curl -s -X GET "$API_URL/users/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -o profile_response.json
cat profile_response.json
echo

# Test 5: Get strategies
echo -e "\n5. Getting strategies..."
curl -s -X GET "$API_URL/strategies" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -o strategies_response.json
cat strategies_response.json
echo

echo -e "\nAll tests completed!" 