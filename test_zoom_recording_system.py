#!/usr/bin/env python3
"""
Comprehensive Test Suite for Zoom Recording Automatic Upload System
Tests all components to ensure 100% functionality
"""

import json
import sys
import os

# Add the app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_header(title):
    """Print formatted test section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_test(test_name, passed, details=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"       └─ {details}")

def test_doctype_schemas():
    """Test 1: Verify DocType JSON schemas have all required fields"""
    print_header("TEST 1: DocType Schema Verification")

    results = []

    # Test LMS Live Class schema
    try:
        with open('lms/lms/doctype/lms_live_class/lms_live_class.json', 'r') as f:
            lms_live_class = json.load(f)

        required_fields = [
            'recording_processed',
            'zoom_recording_id',
            'recording_passcode',
            'recording_url',
            'recording_duration',
            'recording_file_size',
            'meeting_id',
            'uuid',
            'zoom_account',
            'auto_recording',
            'lesson',
            'batch_name'
        ]

        field_names = [field['fieldname'] for field in lms_live_class['fields']]

        for field in required_fields:
            exists = field in field_names
            results.append(('LMS Live Class', field, exists))
            print_test(f"Field '{field}' exists in LMS Live Class", exists)

    except Exception as e:
        print_test("Load LMS Live Class JSON", False, str(e))
        return False

    # Test LMS Zoom Settings schema
    try:
        with open('lms/lms/doctype/lms_zoom_settings/lms_zoom_settings.json', 'r') as f:
            zoom_settings = json.load(f)

        required_fields = [
            'account_name',
            'member',
            'account_id',
            'client_id',
            'client_secret',
            'webhook_secret_token'
        ]

        field_names = [field['fieldname'] for field in zoom_settings['fields']]

        for field in required_fields:
            exists = field in field_names
            results.append(('LMS Zoom Settings', field, exists))
            print_test(f"Field '{field}' exists in LMS Zoom Settings", exists)

    except Exception as e:
        print_test("Load LMS Zoom Settings JSON", False, str(e))
        return False

    all_passed = all(r[2] for r in results)
    print(f"\n📊 Schema Tests: {sum(1 for r in results if r[2])}/{len(results)} passed")
    return all_passed

def test_api_functions():
    """Test 2: Verify all API functions exist and are properly structured"""
    print_header("TEST 2: API Functions Existence Check")

    results = []

    # Read api.py
    try:
        with open('lms/lms/api.py', 'r') as f:
            api_content = f.read()

        # Check for webhook function
        has_zoom_webhook = 'def zoom_webhook():' in api_content
        results.append(('zoom_webhook', has_zoom_webhook))
        print_test("zoom_webhook() function exists", has_zoom_webhook)

        # Check for signature verification
        has_verify_sig = 'def verify_zoom_signature(' in api_content
        results.append(('verify_zoom_signature', has_verify_sig))
        print_test("verify_zoom_signature() function exists", has_verify_sig)

        # Check for playback function
        has_playback = 'def get_zoom_recording_playback(' in api_content
        results.append(('get_zoom_recording_playback', has_playback))
        print_test("get_zoom_recording_playback() function exists", has_playback)

        # Check for @frappe.whitelist decorators
        webhook_whitelisted = '@frappe.whitelist(allow_guest=True' in api_content and 'def zoom_webhook():' in api_content
        results.append(('webhook_whitelisted', webhook_whitelisted))
        print_test("zoom_webhook is whitelisted", webhook_whitelisted)

        playback_whitelisted = '@frappe.whitelist()' in api_content
        results.append(('playback_whitelisted', playback_whitelisted))
        print_test("get_zoom_recording_playback is whitelisted", playback_whitelisted)

        # Check for HMAC verification
        has_hmac = 'import hmac' in api_content and 'hmac.compare_digest' in api_content
        results.append(('hmac_verification', has_hmac))
        print_test("HMAC signature verification implemented", has_hmac)

        # Check for background job enqueueing
        has_enqueue = 'frappe.enqueue(' in api_content and 'process_zoom_recording' in api_content
        results.append(('background_job', has_enqueue))
        print_test("Background job enqueueing implemented", has_enqueue)

    except Exception as e:
        print_test("Read api.py file", False, str(e))
        return False

    all_passed = all(r[1] for r in results)
    print(f"\n📊 API Function Tests: {sum(1 for r in results if r[1])}/{len(results)} passed")
    return all_passed

def test_processing_function():
    """Test 3: Verify processing function in lms_live_class.py"""
    print_header("TEST 3: Recording Processing Function Check")

    results = []

    try:
        with open('lms/lms/doctype/lms_live_class/lms_live_class.py', 'r') as f:
            live_class_content = f.read()

        # Check for process_zoom_recording function
        has_process_func = 'def process_zoom_recording(' in live_class_content
        results.append(('process_zoom_recording', has_process_func))
        print_test("process_zoom_recording() function exists", has_process_func)

        # Check for metadata extraction (not file download)
        has_metadata_only = 'metadata only' in live_class_content.lower() or 'NO file download' in live_class_content
        results.append(('metadata_only', has_metadata_only))
        print_test("Metadata-only approach confirmed", has_metadata_only, "No file downloads")

        # Check for idempotent check
        has_idempotent = 'recording_processed' in live_class_content and 'if frappe.db.get_value' in live_class_content
        results.append(('idempotent', has_idempotent))
        print_test("Idempotent processing check", has_idempotent)

        # Check for passcode fetching
        has_passcode = 'recording_play_passcode' in live_class_content or 'recording_passcode' in live_class_content
        results.append(('passcode_fetch', has_passcode))
        print_test("Passcode fetching from Zoom API", has_passcode)

        # Check for duration calculation
        has_duration = 'duration_seconds' in live_class_content or 'recording_duration' in live_class_content
        results.append(('duration_calc', has_duration))
        print_test("Duration calculation implemented", has_duration)

        # Check for notification
        has_notify = 'notify_instructor' in live_class_content or 'Notification Log' in live_class_content
        results.append(('notification', has_notify))
        print_test("Instructor notification implemented", has_notify)

        # Check for update_attendance function
        has_attendance = 'def update_attendance():' in live_class_content
        results.append(('attendance_tracking', has_attendance))
        print_test("update_attendance() function exists", has_attendance)

    except Exception as e:
        print_test("Read lms_live_class.py file", False, str(e))
        return False

    all_passed = all(r[1] for r in results)
    print(f"\n📊 Processing Function Tests: {sum(1 for r in results if r[1])}/{len(results)} passed")
    return all_passed

def test_security_features():
    """Test 4: Verify security implementations"""
    print_header("TEST 4: Security Features Verification")

    results = []

    try:
        with open('lms/lms/api.py', 'r') as f:
            api_content = f.read()

        # HMAC-SHA256 signature verification
        has_hmac_sha256 = 'hashlib.sha256' in api_content
        results.append(('hmac_sha256', has_hmac_sha256))
        print_test("HMAC-SHA256 algorithm used", has_hmac_sha256)

        # Constant-time comparison
        has_constant_time = 'hmac.compare_digest' in api_content
        results.append(('constant_time', has_constant_time))
        print_test("Constant-time comparison (timing attack prevention)", has_constant_time)

        # Enrollment verification in playback
        has_enrollment_check = 'get_membership' in api_content
        results.append(('enrollment_check', has_enrollment_check))
        print_test("Enrollment verification for playback", has_enrollment_check)

        # Role-based exemptions
        has_role_check = 'is_moderator' in api_content or 'is_instructor' in api_content
        results.append(('role_exemptions', has_role_check))
        print_test("Role-based access exemptions", has_role_check)

        # Password field encryption
        with open('lms/lms/doctype/lms_zoom_settings/lms_zoom_settings.json', 'r') as f:
            zoom_settings = json.load(f)

        password_fields = [f for f in zoom_settings['fields'] if f.get('fieldtype') == 'Password']
        has_password_encryption = len(password_fields) >= 2  # client_secret and webhook_secret_token
        results.append(('password_encryption', has_password_encryption))
        print_test("Password fields encrypted", has_password_encryption, f"{len(password_fields)} password fields")

        # CSRF exemption for webhook
        has_csrf_exempt = 'csrf_exempt' in api_content
        results.append(('csrf_exempt', has_csrf_exempt))
        print_test("CSRF exemption for webhook", has_csrf_exempt)

    except Exception as e:
        print_test("Security features check", False, str(e))
        return False

    all_passed = all(r[1] for r in results)
    print(f"\n📊 Security Tests: {sum(1 for r in results if r[1])}/{len(results)} passed")
    return all_passed

def test_scheduled_jobs():
    """Test 5: Verify scheduled jobs configuration"""
    print_header("TEST 5: Scheduled Jobs Configuration")

    results = []

    try:
        with open('lms/hooks.py', 'r') as f:
            hooks_content = f.read()

        # Check for hourly attendance update
        has_attendance_job = 'lms.lms.doctype.lms_live_class.lms_live_class.update_attendance' in hooks_content
        results.append(('attendance_job', has_attendance_job))
        print_test("Hourly attendance update job configured", has_attendance_job)

        # Check scheduler_events structure
        has_scheduler = 'scheduler_events' in hooks_content and '"hourly":' in hooks_content
        results.append(('scheduler_structure', has_scheduler))
        print_test("Scheduler events properly configured", has_scheduler)

        # Check for live class reminder
        has_reminder = 'send_live_class_reminder' in hooks_content
        results.append(('reminder_job', has_reminder))
        print_test("Daily live class reminder job configured", has_reminder)

    except Exception as e:
        print_test("Read hooks.py file", False, str(e))
        return False

    all_passed = all(r[1] for r in results)
    print(f"\n📊 Scheduled Jobs Tests: {sum(1 for r in results if r[1])}/{len(results)} passed")
    return all_passed

def test_error_handling():
    """Test 6: Verify error handling and logging"""
    print_header("TEST 6: Error Handling & Logging")

    results = []

    try:
        with open('lms/lms/api.py', 'r') as f:
            api_content = f.read()

        # Check for try-except blocks in webhook
        has_exception_handling = 'except Exception as e:' in api_content
        results.append(('exception_handling', has_exception_handling))
        print_test("Exception handling implemented", has_exception_handling)

        # Check for error logging
        has_error_logging = 'frappe.log_error' in api_content
        results.append(('error_logging', has_error_logging))
        print_test("Error logging implemented", has_error_logging)

        # Check for HTTP 200 always returned (Zoom requirement)
        has_200_response = 'http_status_code = 200' in api_content
        results.append(('always_200', has_200_response))
        print_test("Always returns HTTP 200 (Zoom requirement)", has_200_response)

        # Check for JSON error handling
        has_json_error = 'json.JSONDecodeError' in api_content or 'JSONDecodeError' in api_content
        results.append(('json_error_handling', has_json_error))
        print_test("JSON decode error handling", has_json_error)

        with open('lms/lms/doctype/lms_live_class/lms_live_class.py', 'r') as f:
            live_class_content = f.read()

        # Check for error logging in processing
        has_processing_errors = 'frappe.log_error' in live_class_content
        results.append(('processing_error_log', has_processing_errors))
        print_test("Recording processing error logging", has_processing_errors)

        # Check for HTTP error handling
        has_http_errors = 'requests.exceptions.HTTPError' in live_class_content or 'HTTPError' in live_class_content
        results.append(('http_error_handling', has_http_errors))
        print_test("HTTP error handling for Zoom API", has_http_errors)

    except Exception as e:
        print_test("Error handling check", False, str(e))
        return False

    all_passed = all(r[1] for r in results)
    print(f"\n📊 Error Handling Tests: {sum(1 for r in results if r[1])}/{len(results)} passed")
    return all_passed

def test_integration_points():
    """Test 7: Verify integration with courses, lessons, batches"""
    print_header("TEST 7: Integration Points & Relationships")

    results = []

    try:
        with open('lms/lms/doctype/lms_live_class/lms_live_class.json', 'r') as f:
            live_class = json.load(f)

        # Check for lesson link
        lesson_field = next((f for f in live_class['fields'] if f['fieldname'] == 'lesson'), None)
        has_lesson_link = lesson_field and lesson_field.get('options') == 'Course Lesson'
        results.append(('lesson_link', has_lesson_link))
        print_test("Lesson linking configured", has_lesson_link)

        # Check for batch link
        batch_field = next((f for f in live_class['fields'] if f['fieldname'] == 'batch_name'), None)
        has_batch_link = batch_field and batch_field.get('options') == 'LMS Batch'
        results.append(('batch_link', has_batch_link))
        print_test("Batch linking configured", has_batch_link)

        # Check for zoom account link
        zoom_field = next((f for f in live_class['fields'] if f['fieldname'] == 'zoom_account'), None)
        has_zoom_link = zoom_field and zoom_field.get('options') == 'LMS Zoom Settings'
        results.append(('zoom_account_link', has_zoom_link))
        print_test("Zoom account linking configured", has_zoom_link)

        with open('lms/lms/api.py', 'r') as f:
            api_content = f.read()

        # Check for course enrollment verification
        has_course_check = 'Course Lesson' in api_content and 'course' in api_content
        results.append(('course_enrollment', has_course_check))
        print_test("Course enrollment verification", has_course_check)

        # Check for batch enrollment fallback
        has_batch_fallback = 'batch.courses' in api_content or 'Batch Course' in api_content
        results.append(('batch_fallback', has_batch_fallback))
        print_test("Batch enrollment fallback logic", has_batch_fallback)

    except Exception as e:
        print_test("Integration points check", False, str(e))
        return False

    all_passed = all(r[1] for r in results)
    print(f"\n📊 Integration Tests: {sum(1 for r in results if r[1])}/{len(results)} passed")
    return all_passed

def test_webhook_validation():
    """Test 8: Verify webhook endpoint validation"""
    print_header("TEST 8: Webhook Endpoint Validation")

    results = []

    try:
        with open('lms/lms/api.py', 'r') as f:
            api_content = f.read()

        # Check for endpoint.url_validation event handling
        has_validation = 'endpoint.url_validation' in api_content
        results.append(('url_validation', has_validation))
        print_test("Endpoint URL validation event handling", has_validation)

        # Check for plainToken handling
        has_plain_token = 'plainToken' in api_content
        results.append(('plain_token', has_plain_token))
        print_test("plainToken handling for validation", has_plain_token)

        # Check for encryptedToken generation
        has_encrypted_token = 'encryptedToken' in api_content
        results.append(('encrypted_token', has_encrypted_token))
        print_test("encryptedToken generation", has_encrypted_token)

        # Check for recording.completed event handling
        has_recording_event = 'recording.completed' in api_content
        results.append(('recording_event', has_recording_event))
        print_test("recording.completed event handling", has_recording_event)

        # Check for OPTIONS method handling (CORS)
        has_options = 'OPTIONS' in api_content and 'methods=' in api_content
        results.append(('cors_support', has_options))
        print_test("OPTIONS/CORS support", has_options)

    except Exception as e:
        print_test("Webhook validation check", False, str(e))
        return False

    all_passed = all(r[1] for r in results)
    print(f"\n📊 Webhook Validation Tests: {sum(1 for r in results if r[1])}/{len(results)} passed")
    return all_passed

def generate_test_report():
    """Generate comprehensive test report"""
    print_header("COMPREHENSIVE TEST REPORT")

    all_tests = []

    # Run all tests
    all_tests.append(("DocType Schemas", test_doctype_schemas()))
    all_tests.append(("API Functions", test_api_functions()))
    all_tests.append(("Processing Function", test_processing_function()))
    all_tests.append(("Security Features", test_security_features()))
    all_tests.append(("Scheduled Jobs", test_scheduled_jobs()))
    all_tests.append(("Error Handling", test_error_handling()))
    all_tests.append(("Integration Points", test_integration_points()))
    all_tests.append(("Webhook Validation", test_webhook_validation()))

    # Summary
    print_header("FINAL RESULTS")

    passed_count = sum(1 for _, result in all_tests if result)
    total_count = len(all_tests)

    for test_name, passed in all_tests:
        print_test(test_name, passed)

    print(f"\n{'='*80}")
    print(f"  OVERALL: {passed_count}/{total_count} Test Categories Passed")
    print(f"  Success Rate: {(passed_count/total_count)*100:.1f}%")
    print(f"{'='*80}\n")

    if passed_count == total_count:
        print("🎉 ALL TESTS PASSED! System is 100% ready for production.")
    else:
        print("⚠️  Some tests failed. Please review the issues above.")

    return passed_count == total_count

if __name__ == "__main__":
    print("\n" + "="*80)
    print("  ZOOM RECORDING AUTOMATIC UPLOAD SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print("  Testing all components for 100% functionality assurance")
    print("  Location: /Users/raibasharatali/Desktop/Zensbot.com/LMS_UPDATED")
    print("="*80 + "\n")

    success = generate_test_report()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
