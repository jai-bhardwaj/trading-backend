#!/bin/bash

# This script creates a mock (paper) order using the API
# Requires: jq, login_response.json, profile_response.json

API_URL="http://localhost:8000/orders"
TOKEN=$(jq -r .access_token < login_response.json)
USER_ID=$(jq -r .id < profile_response.json)

if [[ -z "$TOKEN" || -z "$USER_ID" ]]; then
  echo "Error: Missing token or user ID. Please ensure login_response.json and profile_response.json exist."
  exit 1
fi

ORDER_PAYLOAD=$(cat <<EOF
{
  "user_id": "$USER_ID",
  "symbol": "SBIN-EQ",
  "exchange": "NSE",
  "product_type": "INTRADAY",
  "order_type": "LIMIT",
  "side": "BUY",
  "quantity": 10,
  "price": 350.50,
  "trigger_price": 348.00,
  "variety": "NORMAL",
  "tag": "test_order",
  "broker_id": "mock_broker",
  "is_paper_trade": true
}
EOF
)

curl -X POST "$API_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$ORDER_PAYLOAD" | jq 