#!/bin/bash

# Test Vimeo Webhook with Actual Payload Format
# This tests the exact payload format that Vimeo Zoom app sends

echo "===================================="
echo "Vimeo Webhook - Actual Payload Test"
echo "===================================="
echo ""

WEBHOOK_URL="https://lms.ictpk.cloud/webhook/vimeo"

echo "Testing with actual Vimeo Zoom app payload format..."
echo "----------------------------------------------------"
echo ""

echo "Payload:"
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

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_type": "video-created",
    "data": {
      "clip_uri": "/videos/1153210218",
      "video_uri": "/videos/1153210218"
    },
    "timestamp": 1768072665
  }' \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -v

echo ""
echo "===================================="
echo "Expected Results:"
echo "===================================="
echo ""
echo "✓ HTTP Status: 200 (not 500)"
echo "✓ Response: {\"status\": \"success\", ...}"
echo ""
echo "✓ Logs should show:"
echo "  - [Vimeo Webhook] Event type: video-created"
echo "  - [Vimeo Webhook] Extracting video ID from URI: /videos/1153210218"
echo "  - [Vimeo Webhook] Constructed URL from URI: ... -> https://player.vimeo.com/video/1153210218"
echo "  - [Vimeo Webhook] Converted Unix timestamp 1768072665 to ..."
echo ""
echo "Check backend logs:"
echo "docker logs backend-lms-1 --tail 50 | grep \"Vimeo Webhook\""
echo ""
