#!/usr/bin/env python3
"""
Test script for Zoom webhook endpoint validation.

Usage:
    python3 test_zoom_webhook.py https://lms.ictpk.cloud

This script:
1. Sends a validation request to the webhook endpoint
2. Checks the response format and status
3. Verifies HMAC calculation (if webhook secret is provided)
"""

import sys
import json
import hmac
import hashlib
import requests

def test_zoom_webhook_validation(base_url, webhook_secret=None):
    """Test Zoom webhook endpoint validation"""

    # Construct webhook URL
    webhook_url = f"{base_url}/api/method/lms.lms.api.zoom_webhook"

    # Test payload - simulating Zoom's validation request
    test_plain_token = "test_token_12345_abcdef"
    payload = {
        "event": "endpoint.url_validation",
        "payload": {
            "plainToken": test_plain_token
        }
    }

    print(f"\n{'='*60}")
    print("ZOOM WEBHOOK ENDPOINT VALIDATION TEST")
    print(f"{'='*60}\n")

    print(f"Testing endpoint: {webhook_url}")
    print(f"Sending plainToken: {test_plain_token}\n")

    # Send POST request
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}\n")

        # Check HTTP status
        if response.status_code != 200:
            print(f"❌ FAILED: Expected HTTP 200, got {response.status_code}")
            print(f"Response body: {response.text}")
            return False
        else:
            print("✅ HTTP 200 OK")

        # Check Content-Type
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            print(f"⚠️  WARNING: Content-Type is '{content_type}', expected 'application/json'")
        else:
            print("✅ Content-Type: application/json")

        # Parse JSON response
        try:
            response_data = response.json()
            print(f"\nResponse JSON:")
            print(json.dumps(response_data, indent=2))
        except json.JSONDecodeError as e:
            print(f"❌ FAILED: Response is not valid JSON: {e}")
            print(f"Response body: {response.text}")
            return False

        # Check response structure
        if not isinstance(response_data, dict):
            print(f"❌ FAILED: Response is not a JSON object (dict), it's a {type(response_data)}")
            return False
        else:
            print("\n✅ Response is a JSON object (dict)")

        # Check required fields
        if "plainToken" not in response_data:
            print("❌ FAILED: Response missing 'plainToken' field")
            return False
        else:
            print(f"✅ Found 'plainToken': {response_data['plainToken']}")

        if "encryptedToken" not in response_data:
            print("❌ FAILED: Response missing 'encryptedToken' field")
            return False
        else:
            print(f"✅ Found 'encryptedToken': {response_data['encryptedToken']}")

        # Verify plainToken matches
        if response_data["plainToken"] != test_plain_token:
            print(f"❌ FAILED: plainToken mismatch")
            print(f"  Expected: {test_plain_token}")
            print(f"  Received: {response_data['plainToken']}")
            return False
        else:
            print("✅ plainToken matches input")

        # Check encryptedToken format (should be hex string)
        encrypted_token = response_data["encryptedToken"]
        if not isinstance(encrypted_token, str):
            print(f"❌ FAILED: encryptedToken is not a string, it's {type(encrypted_token)}")
            return False

        # Should be 64 characters (SHA-256 hex = 256 bits / 4 bits per hex char = 64 chars)
        if len(encrypted_token) != 64:
            print(f"⚠️  WARNING: encryptedToken length is {len(encrypted_token)}, expected 64 (SHA-256 hex)")

        # Should be lowercase hex (no uppercase, no base64 characters)
        if not all(c in "0123456789abcdef" for c in encrypted_token):
            print(f"⚠️  WARNING: encryptedToken contains non-hex characters (should be lowercase hex)")
            print(f"  Token: {encrypted_token}")
        else:
            print("✅ encryptedToken is lowercase hex string")

        # If webhook_secret provided, verify HMAC calculation
        if webhook_secret:
            print(f"\nVerifying HMAC calculation with provided webhook secret...")
            expected_encrypted = hmac.new(
                webhook_secret.encode("utf-8"),
                test_plain_token.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            if encrypted_token == expected_encrypted:
                print("✅ HMAC calculation is correct!")
            else:
                print("❌ FAILED: HMAC calculation mismatch")
                print(f"  Expected: {expected_encrypted}")
                print(f"  Received: {encrypted_token}")
                print("\n  Possible issues:")
                print("  - Webhook secret token in LMS doesn't match the one you provided")
                print("  - HMAC calculation method is incorrect")
                return False
        else:
            print("\n⚠️  Skipping HMAC verification (no webhook_secret provided)")
            print("   To verify HMAC, run: python3 test_zoom_webhook.py <url> <webhook_secret>")

        print(f"\n{'='*60}")
        print("✅ ALL TESTS PASSED!")
        print(f"{'='*60}\n")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Request error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_zoom_webhook.py <base_url> [webhook_secret]")
        print("Example: python3 test_zoom_webhook.py https://lms.ictpk.cloud")
        print("Example: python3 test_zoom_webhook.py https://lms.ictpk.cloud YOUR_WEBHOOK_SECRET")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    webhook_secret = sys.argv[2] if len(sys.argv) > 2 else None

    success = test_zoom_webhook_validation(base_url, webhook_secret)
    sys.exit(0 if success else 1)
