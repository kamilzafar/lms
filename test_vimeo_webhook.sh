#!/bin/bash

# Test Vimeo Webhook Endpoint
# Tests the webhook with various payloads to ensure it handles them correctly

echo "=================================="
echo "Vimeo Webhook Test Suite"
echo "=================================="
echo ""

WEBHOOK_URL="https://lms.ictpk.cloud/webhook/vimeo"

# Test 1: Basic video upload complete
echo "Test 1: Video Upload Complete Event"
echo "-----------------------------------"
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "video.upload.complete",
    "data": {
      "name": "Test Recording - Do Not Match",
      "player_embed_url": "https://player.vimeo.com/video/999999999",
      "link": "https://vimeo.com/999999999",
      "created_time": "2026-01-11T15:46:00Z",
      "description": "Test video for webhook verification",
      "duration": 3600
    }
  }'
echo -e "\n"

# Test 2: Direct Vimeo link (should normalize to player URL)
echo ""
echo "Test 2: Direct Vimeo Link (URL Normalization)"
echo "---------------------------------------------"
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "video.upload.complete",
    "data": {
      "name": "Test Recording - URL Normalization",
      "link": "https://vimeo.com/1153312262?share=copy&fl=sv&fe=ci",
      "created_time": "2026-01-11T16:00:00Z",
      "description": "Test URL normalization",
      "duration": 1800
    }
  }'
echo -e "\n"

# Test 3: Video with meeting ID in description
echo ""
echo "Test 3: Video with Meeting ID in Description"
echo "--------------------------------------------"
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "video.upload.complete",
    "data": {
      "name": "Test Recording - Meeting ID Match",
      "player_embed_url": "https://player.vimeo.com/video/888888888",
      "created_time": "2026-01-11T16:15:00Z",
      "description": "Zoom Meeting recorded. Meeting ID: 12345678901",
      "duration": 2400
    }
  }'
echo -e "\n"

# Test 4: Alternative event name
echo ""
echo "Test 4: Alternative Event Name (video.upload.success)"
echo "-----------------------------------------------------"
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "video.upload.success",
    "data": {
      "name": "Test Recording - Alternative Event",
      "player_embed_url": "https://player.vimeo.com/video/777777777",
      "created_time": "2026-01-11T16:30:00Z"
    }
  }'
echo -e "\n"

# Test 5: Verification challenge (webhook setup)
echo ""
echo "Test 5: Webhook Verification Challenge"
echo "--------------------------------------"
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "verification",
    "challenge": "test-challenge-12345"
  }'
echo -e "\n"

# Test 6: GET request (should return error but not crash)
echo ""
echo "Test 6: GET Request (should return error gracefully)"
echo "---------------------------------------------------"
curl -X GET "$WEBHOOK_URL"
echo -e "\n"

echo ""
echo "=================================="
echo "Test Suite Complete"
echo "=================================="
echo ""
echo "Expected Results:"
echo "- Tests 1-4: Should return {\"status\": \"success\", ...}"
echo "- Test 5: Should return {\"challenge\": \"test-challenge-12345\"}"
echo "- Test 6: Should return {\"status\": \"error\", \"message\": \"No data received\"}"
echo ""
echo "Check backend logs for detailed processing:"
echo "docker logs backend-lms-1 -f | grep \"Vimeo Webhook\""
echo ""
