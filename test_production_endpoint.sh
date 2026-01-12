#!/bin/bash

# Quick test script to verify production endpoint is working
# Run this AFTER deploying the code to production

echo "========================================="
echo "Testing Production Endpoint"
echo "========================================="
echo ""
echo "Testing: https://lms.ictpk.cloud/api/method/lms.lms.api.process_vimeo_recording"
echo ""

# Test with minimal payload
echo "Sending test request..."
echo ""

RESPONSE=$(curl -X POST https://lms.ictpk.cloud/api/method/lms.lms.api.process_vimeo_recording \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://player.vimeo.com/video/1153210218",
    "video_id": "1153210218"
  }' \
  -w "\n---HTTP_STATUS:%{http_code}---" \
  -s)

# Extract HTTP status
HTTP_STATUS=$(echo "$RESPONSE" | grep -oP '(?<=---HTTP_STATUS:)\d+(?=---)')
BODY=$(echo "$RESPONSE" | sed 's/---HTTP_STATUS:[0-9]*---//')

echo "Response:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
echo ""
echo "HTTP Status: $HTTP_STATUS"
echo ""

# Check result
if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ SUCCESS! Endpoint is working (HTTP 200)"
    echo ""
    echo "Next steps:"
    echo "1. Update your n8n HTTP Request node with the fixed configuration"
    echo "2. Test your n8n workflow"
    echo "3. Check LMS logs: docker logs backend-lms-1 --tail 100 | grep '[n8n Vimeo]'"
elif [ "$HTTP_STATUS" = "417" ]; then
    echo "❌ FAILED! Still getting 417 error"
    echo ""
    echo "This means the function is NOT deployed to production yet."
    echo ""
    echo "Action required:"
    echo "1. SSH to production server"
    echo "2. Navigate to: /path/to/frappe-bench/apps/lms"
    echo "3. Run: git pull origin develop"
    echo "4. Run: docker restart backend-lms-1"
    echo "5. Wait 30 seconds, then run this script again"
elif [ "$HTTP_STATUS" = "000" ]; then
    echo "❌ FAILED! Could not connect to server"
    echo ""
    echo "Possible causes:"
    echo "- Server is down"
    echo "- Network connectivity issue"
    echo "- Wrong URL"
else
    echo "⚠️  Unexpected HTTP status: $HTTP_STATUS"
    echo ""
    echo "Check the response body above for details"
fi

echo ""
echo "========================================="
