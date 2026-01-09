# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _
from frappe.model.document import Document


class LMSVimeoSettings(Document):
	def before_save(self):
		self._set_webhook_url()

	def validate(self):
		self._set_webhook_url()
		if self.enabled:
			self._verify_credentials()

	def _set_webhook_url(self):
		"""Set the webhook URL for Vimeo notifications"""
		base_url = frappe.utils.get_url()
		self.webhook_url = f"{base_url}/api/method/lms.lms.api.vimeo_webhook"

	def _verify_credentials(self):
		"""Verify Vimeo API credentials by making a test API call"""
		try:
			access_token = self.get_password("access_token", raise_exception=False)
			if not access_token:
				self.verification_status = "Missing access token"
				return

			headers = {
				"Authorization": f"Bearer {access_token}",
				"Content-Type": "application/json",
				"Accept": "application/vnd.vimeo.*+json;version=3.4"
			}

			response = requests.get(
				"https://api.vimeo.com/me",
				headers=headers,
				timeout=10
			)

			if response.status_code == 200:
				data = response.json()
				user_name = data.get("name", "Unknown")
				self.verification_status = f"Connected as: {user_name}"
				self.last_verified = frappe.utils.now()
				frappe.logger().info(f"[Vimeo Settings] Credentials verified for {self.account_name}")
			elif response.status_code == 401:
				self.verification_status = "Invalid credentials"
				frappe.logger().error(f"[Vimeo Settings] Invalid credentials for {self.account_name}")
			else:
				self.verification_status = f"Error: {response.status_code}"
				frappe.logger().error(f"[Vimeo Settings] Verification failed: {response.status_code} - {response.text}")

		except requests.exceptions.Timeout:
			self.verification_status = "Connection timeout"
			frappe.logger().error(f"[Vimeo Settings] Connection timeout for {self.account_name}")
		except requests.exceptions.RequestException as e:
			self.verification_status = f"Connection error: {str(e)[:50]}"
			frappe.logger().error(f"[Vimeo Settings] Connection error for {self.account_name}: {str(e)}")
		except Exception as e:
			self.verification_status = f"Error: {str(e)[:50]}"
			frappe.logger().error(f"[Vimeo Settings] Unexpected error for {self.account_name}: {str(e)}")


def get_vimeo_settings():
	"""Get the first enabled Vimeo settings document"""
	settings = frappe.get_all(
		"LMS Vimeo Settings",
		filters={"enabled": 1},
		fields=["name"],
		limit=1
	)

	if not settings:
		return None

	return frappe.get_doc("LMS Vimeo Settings", settings[0].name)


def get_vimeo_access_token():
	"""Get the access token from enabled Vimeo settings"""
	settings = get_vimeo_settings()
	if not settings:
		return None

	return settings.get_password("access_token", raise_exception=False)
