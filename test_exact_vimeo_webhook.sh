#!/bin/bash

# Test Vimeo Webhook with EXACT Format from Vimeo
# This matches the exact webhook payload that Vimeo Zoom app sends

echo "========================================="
echo "Vimeo Webhook - EXACT Format Test"
echo "========================================="
echo ""
echo "Testing with the EXACT webhook format you receive from Vimeo"
echo ""

WEBHOOK_URL="https://lms.ictpk.cloud/webhook/vimeo"

echo "Webhook URL: $WEBHOOK_URL"
echo ""
echo "Payload (exact format from Vimeo):"
echo '{'
echo '  "webhook_type": "video-created",'
echo '  "data": {'
echo '    "clip_uri": "/videos/1153210218",'
echo '    "video_uri": "/videos/1153210218"'
echo '  },'
echo '  "timestamp": 1768072665'
echo '}'
echo ""
echo "Sending request..."
echo ""

# Send the request
response=$(curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: test-signature-not-verified" \
  -d '{
    "webhook_type": "video-created",
    "data": {
      "clip_uri": "/videos/1153210218",
      "video_uri": "/videos/1153210218"
    },
    "timestamp": 1768072665
  }' \
  -s -w "\n\nHTTP Status Code: %{http_code}\n")

echo "$response"
echo ""
echo "========================================="
echo "Analysis"
echo "========================================="
echo ""

# Check if 200 or 500
if echo "$response" | grep -q "HTTP Status Code: 200"; then
  echo "✅ SUCCESS: HTTP 200 - Webhook processed successfully"
elif echo "$response" | grep -q "HTTP Status Code: 500"; then
  echo "❌ FAIL: HTTP 500 - Internal Server Error"
  echo ""
  echo "This means there's still an issue in the code."
  echo "Check backend logs for details:"
  echo "  docker logs backend-lms-1 --tail 100 | grep -A 20 Traceback"
else
  echo "⚠️  UNKNOWN: Unexpected response"
fi

echo ""

# Check response body
if echo "$response" | grep -q '"status".*"success"'; then
  echo "✅ Response contains success status"
fi

if echo "$response" | grep -q "Recording updated with Vimeo URL"; then
  echo "✅ Live Class was matched and updated"
elif echo "$response" | grep -q "No matching live class found"; then
  echo "ℹ️  No matching Live Class (expected if no class within ±24 hours)"
fi

echo ""
echo "========================================="
echo "Expected Behavior"
echo "========================================="
echo ""
echo "1. HTTP Status: 200 (not 500)"
echo "2. Response body: {\"status\": \"success\", ...}"
echo ""
echo "If matching Live Class found:"
echo "  - Response: \"Recording updated with Vimeo URL for LMS-LC-XXXXX\""
echo "  - Live Class recording_url updated to: https://player.vimeo.com/video/1153210218"
echo "  - Lesson auto-created in \"Recordings\" chapter"
echo ""
echo "If no matching Live Class:"
echo "  - Response: \"No matching live class found (might not be LMS recording)\""
echo "  - This is OK - means no Live Class within ±24 hours of timestamp"
echo ""
echo "========================================="
echo "Backend Logs"
echo "========================================="
echo ""
echo "Check logs with:"
echo "  docker logs backend-lms-1 --tail 50 | grep 'Vimeo Webhook'"
echo ""
echo "Expected log output:"
echo "  [Vimeo Webhook] Received payload: {...}"
echo "  [Vimeo Webhook] Event type: video-created"
echo "  [Vimeo Webhook] Extracting video ID from URI: /videos/1153210218"
echo "  [Vimeo Webhook] Constructed URL from URI: ... -> https://player.vimeo.com/video/1153210218"
echo "  [Vimeo Webhook] Converted Unix timestamp 1768072665 to ..."
echo "  [Vimeo Webhook] Video uploaded: title='', url=https://player.vimeo.com/video/1153210218"
echo ""
echo "If signature warning (OK - not critical):"
echo "  [Vimeo Webhook] Signature present but no vimeo_webhook_secret configured"
echo ""
