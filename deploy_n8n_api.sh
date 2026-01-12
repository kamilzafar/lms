#!/bin/bash

# Deploy n8n Vimeo API to Production
# Run this script to deploy the new endpoint

echo "========================================="
echo "Deploying n8n Vimeo API to Production"
echo "========================================="
echo ""

# Check if function exists locally
echo "1. Checking local api.py..."
if grep -q "def process_vimeo_recording" lms/lms/api.py; then
    echo "   ✅ Function found in local file"
    line_count=$(wc -l < lms/lms/api.py)
    echo "   ✅ File has $line_count lines"
else
    echo "   ❌ Function NOT found in local file!"
    exit 1
fi

echo ""
echo "2. Deploying to production..."
echo ""

# Option 1: Git push (recommended)
echo "Option 1: Using Git"
echo "-------------------"
echo "Run these commands:"
echo ""
echo "  git add lms/lms/api.py"
echo "  git commit -m 'Add process_vimeo_recording API for n8n integration'"
echo "  git push origin develop"
echo ""
echo "Then on production server:"
echo "  cd /path/to/frappe-bench/apps/lms"
echo "  git pull origin develop"
echo "  docker restart backend-lms-1"
echo ""

# Option 2: Direct copy
echo "Option 2: Direct Copy (if SSH access)"
echo "--------------------------------------"
echo "Replace with your server details and run:"
echo ""
echo "  scp lms/lms/api.py user@lms.ictpk.cloud:/path/to/frappe-bench/apps/lms/lms/lms/"
echo "  ssh user@lms.ictpk.cloud 'docker restart backend-lms-1'"
echo ""

echo "========================================="
echo "After Deployment"
echo "========================================="
echo ""
echo "Test the endpoint:"
echo ""
echo "curl -X POST https://lms.ictpk.cloud/api/method/lms.lms.api.process_vimeo_recording \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"video_url\": \"https://player.vimeo.com/video/1153210218\", \"video_id\": \"1153210218\"}'"
echo ""
echo "Expected: JSON response (not 417 error)"
echo ""
