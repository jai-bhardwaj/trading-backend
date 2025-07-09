#!/bin/bash

# Test Slack Notifications
# This script tests the Slack webhook integration

echo "🧪 Testing Slack notifications..."

# Check if SLACK_WEBHOOK_URL is set
if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo "❌ SLACK_WEBHOOK_URL not set in environment"
    echo "Please add SLACK_WEBHOOK_URL to your .env file"
    exit 1
fi

# Test basic notification
echo "📡 Sending test notification to Slack..."
curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"🧪 Trading Backend Slack Test - System is working!"}' \
    "$SLACK_WEBHOOK_URL"

if [ $? -eq 0 ]; then
    echo "✅ Slack notification test successful!"
    echo "Check your Slack channel for the test message"
else
    echo "❌ Slack notification test failed"
    echo "Please check your SLACK_WEBHOOK_URL"
fi

# Test error notification format
echo "📡 Sending error notification test..."
curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"🚨 Trading Backend Error Test:\nTest error message\nTimestamp: $(date)\"}" \
    "$SLACK_WEBHOOK_URL"

echo "✅ Error notification test completed" 