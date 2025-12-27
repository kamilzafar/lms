#!/usr/bin/env python3
"""
Quick verification script to ensure Zoom webhook returns RAW JSON object, not a string.

Usage: python3 verify_zoom_response.py https://lms.ictpk.cloud
"""

import sys
import json
import requests

def verify_response_is_json_object(base_url):
    """Verify the webhook returns a JSON object, not a JSON string"""

    webhook_url = f"{base_url}/api/method/lms.lms.api.zoom_webhook"

    payload = {
        "event": "endpoint.url_validation",
        "payload": {
            "plainToken": "test_verification_token"
        }
    }

    print("=" * 70)
    print("ZOOM WEBHOOK RESPONSE VERIFICATION")
    print("=" * 70)
    print(f"\nEndpoint: {webhook_url}")
    print(f"Testing with plainToken: {payload['payload']['plainToken']}\n")

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)

        # Check HTTP status
        print(f"1. HTTP Status Code: {response.status_code}")
        if response.status_code != 200:
            print(f"   ❌ FAIL: Expected 200, got {response.status_code}")
            return False
        print("   ✅ PASS: HTTP 200 OK")

        # Check Content-Type header
        content_type = response.headers.get("Content-Type", "")
        print(f"\n2. Content-Type Header: {content_type}")
        if "application/json" not in content_type.lower():
            print(f"   ⚠️  WARNING: Expected 'application/json'")
        else:
            print("   ✅ PASS: Content-Type is application/json")

        # Get raw response body
        raw_body = response.text
        print(f"\n3. Raw Response Body:")
        print(f"   Length: {len(raw_body)} bytes")
        print(f"   First 200 chars: {raw_body[:200]}")

        # Critical check: Is response a JSON string or JSON object?
        print(f"\n4. Response Type Check:")

        # Check if response starts with quote (would indicate it's a JSON string)
        if raw_body.strip().startswith('"') and raw_body.strip().endswith('"'):
            print(f"   ❌ FAIL: Response is a JSON STRING, not an object!")
            print(f"   Response starts and ends with quotes: {raw_body[:50]}...{raw_body[-50:]}")
            return False

        # Parse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"   ❌ FAIL: Response is not valid JSON: {e}")
            return False

        # Check if parsed data is a dict (JSON object)
        print(f"   Python type: {type(data)}")
        if not isinstance(data, dict):
            print(f"   ❌ FAIL: Response is not a dict/object, it's {type(data)}")
            return False
        print("   ✅ PASS: Response is a JSON object (dict)")

        # Check for Frappe wrapper patterns
        print(f"\n5. Checking for Frappe Wrappers:")

        if "message" in data and isinstance(data["message"], dict):
            if "plainToken" in data["message"]:
                print(f"   ❌ FAIL: Response is wrapped in 'message' key")
                print(f"   Structure: {json.dumps(data, indent=2)}")
                return False

        if "data" in data and isinstance(data["data"], dict):
            if "plainToken" in data["data"]:
                print(f"   ❌ FAIL: Response is wrapped in 'data' key")
                print(f"   Structure: {json.dumps(data, indent=2)}")
                return False

        print("   ✅ PASS: No Frappe wrappers detected")

        # Check required fields are at root level
        print(f"\n6. Required Fields Check:")

        if "plainToken" not in data:
            print(f"   ❌ FAIL: Missing 'plainToken' at root level")
            print(f"   Available keys: {list(data.keys())}")
            return False
        print(f"   ✅ Found 'plainToken': {data['plainToken']}")

        if "encryptedToken" not in data:
            print(f"   ❌ FAIL: Missing 'encryptedToken' at root level")
            print(f"   Available keys: {list(data.keys())}")
            return False
        print(f"   ✅ Found 'encryptedToken': {data['encryptedToken'][:32]}...")

        # Verify encryptedToken format
        print(f"\n7. encryptedToken Format Check:")
        encrypted = data["encryptedToken"]

        if not isinstance(encrypted, str):
            print(f"   ❌ FAIL: encryptedToken is not a string, it's {type(encrypted)}")
            return False
        print(f"   ✅ encryptedToken is a string")

        if len(encrypted) != 64:
            print(f"   ⚠️  WARNING: Length is {len(encrypted)}, expected 64 (SHA-256 hex)")
        else:
            print(f"   ✅ Length is 64 characters (correct for SHA-256 hex)")

        if not all(c in '0123456789abcdef' for c in encrypted):
            print(f"   ❌ FAIL: Contains non-hex characters (should be lowercase hex)")
            print(f"   encryptedToken: {encrypted}")
            return False
        print(f"   ✅ Is lowercase hex string (no uppercase, no base64)")

        # Final structure check
        print(f"\n8. Final Response Structure:")
        print(json.dumps(data, indent=2))

        if list(data.keys()) == ["plainToken", "encryptedToken"]:
            print("\n   ✅ PERFECT: Response contains exactly plainToken and encryptedToken, nothing else")
        elif set(data.keys()) == {"plainToken", "encryptedToken"}:
            print("\n   ✅ GOOD: Response contains plainToken and encryptedToken")
            print(f"   Note: Also has these keys: {[k for k in data.keys() if k not in ['plainToken', 'encryptedToken']]}")
        else:
            print(f"\n   ⚠️  WARNING: Response has unexpected keys: {list(data.keys())}")

        print("\n" + "=" * 70)
        print("✅ VERIFICATION PASSED - Response is a raw JSON object")
        print("=" * 70)
        print("\nZoom expects:")
        print('  {"plainToken": "...", "encryptedToken": "..."}')
        print("\nYour endpoint returns:")
        print(f'  {json.dumps(data)}')
        print("\n✅ Format matches Zoom requirements!")

        return True

    except requests.exceptions.RequestException as e:
        print(f"\n❌ FAIL: Request error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 verify_zoom_response.py <base_url>")
        print("Example: python3 verify_zoom_response.py https://lms.ictpk.cloud")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    success = verify_response_is_json_object(base_url)
    sys.exit(0 if success else 1)
