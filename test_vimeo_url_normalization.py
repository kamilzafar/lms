#!/usr/bin/env python3
"""
Test Vimeo URL Normalization
Tests that the URL normalization correctly handles various Vimeo URL formats
"""

import re
from urllib.parse import urlparse


def normalize_vimeo_url(vimeo_url):
    """
    Normalize Vimeo URL to player embed format.
    (Replica of the function in api.py for standalone testing)
    """
    if not vimeo_url or "vimeo.com" not in vimeo_url.lower():
        return vimeo_url

    # Already normalized - return as-is
    if "player.vimeo.com" in vimeo_url.lower():
        return vimeo_url

    try:
        parsed = urlparse(vimeo_url)
        path = parsed.path.strip('/')

        # Extract numeric video ID from path
        video_id_match = re.match(r'(\d+)', path)
        if video_id_match:
            video_id = video_id_match.group(1)
            return f"https://player.vimeo.com/video/{video_id}"
        else:
            print(f"WARNING: Could not extract video ID from: {vimeo_url}")
            return vimeo_url
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return vimeo_url


def test_url_normalization():
    """Test various Vimeo URL formats"""

    test_cases = [
        # User's specific format
        {
            "input": "https://vimeo.com/1153312262?share=copy&fl=sv&fe=ci",
            "expected": "https://player.vimeo.com/video/1153312262",
            "description": "User's direct link with query params"
        },
        # Basic formats
        {
            "input": "https://vimeo.com/1153312262",
            "expected": "https://player.vimeo.com/video/1153312262",
            "description": "Basic direct link"
        },
        {
            "input": "https://www.vimeo.com/1153312262",
            "expected": "https://player.vimeo.com/video/1153312262",
            "description": "Direct link with www"
        },
        {
            "input": "https://vimeo.com/123456789?foo=bar",
            "expected": "https://player.vimeo.com/video/123456789",
            "description": "Direct link with query string"
        },
        # Already normalized
        {
            "input": "https://player.vimeo.com/video/1153312262",
            "expected": "https://player.vimeo.com/video/1153312262",
            "description": "Already normalized (should not change)"
        },
        # Edge cases
        {
            "input": "https://vimeo.com/1153312262/",
            "expected": "https://player.vimeo.com/video/1153312262",
            "description": "Direct link with trailing slash"
        },
    ]

    print("=" * 80)
    print("VIMEO URL NORMALIZATION TEST")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        input_url = test["input"]
        expected = test["expected"]
        description = test["description"]

        result = normalize_vimeo_url(input_url)
        success = result == expected

        if success:
            passed += 1
            status = "[PASS]"
        else:
            failed += 1
            status = "[FAIL]"

        print(f"Test {i}: {description}")
        print(f"  Input:    {input_url}")
        print(f"  Expected: {expected}")
        print(f"  Result:   {result}")
        print(f"  Status:   {status}")
        print()

    print("=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    if failed == 0:
        print("\n[SUCCESS] ALL TESTS PASSED! URL normalization is working correctly.")
        return True
    else:
        print(f"\n[ERROR] {failed} TEST(S) FAILED! Please review the implementation.")
        return False


if __name__ == "__main__":
    success = test_url_normalization()
    exit(0 if success else 1)
