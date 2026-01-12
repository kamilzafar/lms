# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VimeoSettings(Document):
	def before_save(self):
		"""Auto-populate webhook URL before saving"""
		self._set_webhook_url()

	def validate(self):
		"""Ensure webhook URL is set"""
		self._set_webhook_url()

	def _set_webhook_url(self):
		"""Set the webhook URL to the clean route"""
		base_url = frappe.utils.get_url()
		self.webhook_url = f"{base_url}/webhook/vimeo"


@frappe.whitelist()
def test_vimeo_connection(access_token):
	"""
	Test if Vimeo access token is valid by calling /me endpoint.

	Args:
		access_token (str): Vimeo API access token

	Returns:
		dict: {"success": bool, "message": str, "user_name": str (if success)}
	"""
	try:
		import requests

		response = requests.get(
			"https://api.vimeo.com/me",
			headers={
				"Authorization": f"Bearer {access_token}",
				"Accept": "application/vnd.vimeo.*+json;version=3.4"
			},
			timeout=10
		)

		if response.status_code == 200:
			data = response.json()
			user_name = data.get("name", "Unknown User")
			return {
				"success": True,
				"message": f"✓ Connection successful! Connected as: {user_name}",
				"user_name": user_name
			}
		elif response.status_code == 401:
			return {
				"success": False,
				"message": "✗ Authentication failed. Invalid access token."
			}
		else:
			return {
				"success": False,
				"message": f"✗ Error {response.status_code}: {response.text[:100]}"
			}

	except requests.exceptions.Timeout:
		return {
			"success": False,
			"message": "✗ Connection timeout. Please check your internet connection."
		}
	except Exception as e:
		return {
			"success": False,
			"message": f"✗ Error: {str(e)}"
		}
