# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LMSZoomSettings(Document):
	def before_save(self):
		# Auto-populate webhook URL with the clean route
		self._set_webhook_url()

	def validate(self):
		# Ensure webhook URL is set
		self._set_webhook_url()

	def _set_webhook_url(self):
		"""Set the webhook URL to the clean route"""
		# Use the cleaner /webhook/zoom route
		base_url = frappe.utils.get_url()
		self.webhook_url = f"{base_url}/webhook/zoom"
