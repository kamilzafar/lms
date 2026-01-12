#!/bin/bash

# Test n8n-based Vimeo API Endpoint
# This tests the new simplified endpoint that n8n will call

echo "========================================="
echo "n8n Vimeo API - Test Script"
echo "========================================="
echo ""
echo "Testing endpoint: /api/method/lms.lms.api.process_vimeo_recording"
echo ""

API_URL="http://localhost:8000/api/method/lms.lms.api.process_vimeo_recording"

# Test 1: Valid payload with all fields
echo "Test 1: Valid payload with all fields"
echo "--------------------------------------"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://player.vimeo.com/video/1153210218",
    "video_id": "1153210218",
    "created_time": "2026-01-11T15:46:00Z",
    "meeting_id": "12345678901",
    "title": "Live Class on Python Basics",
    "description": "Meeting ID: 12345678901",
    "duration": 3600
  }' \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -s

echo ""
echo ""

# Test 2: Minimal payload (only required fields)
echo "Test 2: Minimal payload (required fields only)"
echo "--------------------------------------"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://player.vimeo.com/video/1153210218",
    "video_id": "1153210218"
  }' \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -s

echo ""
echo ""

# Test 3: Missing required field (video_url)
echo "Test 3: Validation error - missing video_url"
echo "--------------------------------------"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "1153210218"
  }' \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -s

echo ""
echo ""

# Test 4: Unix timestamp format
echo "Test 4: Unix timestamp format"
echo "--------------------------------------"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://player.vimeo.com/video/1153210218",
    "video_id": "1153210218",
    "created_time": 1736609160,
    "title": "Test Class"
  }' \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -s

echo ""
echo ""

echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""
echo "Expected Results:"
echo "  - Test 1: HTTP 200, status: success or no match"
echo "  - Test 2: HTTP 200, status: success or no match"
echo "  - Test 3: HTTP 200, status: error, VALIDATION_ERROR"
echo "  - Test 4: HTTP 200, status: success or no match"
echo ""
echo "Check backend logs:"
echo "  docker logs backend-lms-1 --tail 100 | grep '[n8n Vimeo]'"
echo ""
