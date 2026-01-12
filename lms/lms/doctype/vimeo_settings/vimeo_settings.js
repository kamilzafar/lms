// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vimeo Settings", {
	refresh(frm) {
		// Add "Test Connection" button
		if (!frm.is_new()) {
			frm.add_custom_button(__("Test Connection"), function() {
				test_vimeo_connection(frm);
			}).addClass("btn-primary");
		}
	}
});

function test_vimeo_connection(frm) {
	// Get access token value
	let access_token = frm.doc.access_token;

	if (!access_token) {
		frappe.msgprint({
			title: __("Missing Access Token"),
			message: __("Please enter an Access Token before testing the connection."),
			indicator: "red"
		});
		return;
	}

	// Show loading indicator
	frappe.show_alert({
		message: __("Testing connection..."),
		indicator: "blue"
	}, 3);

	// Call server-side test method
	frappe.call({
		method: "lms.lms.doctype.vimeo_settings.vimeo_settings.test_vimeo_connection",
		args: {
			access_token: access_token
		},
		callback: function(r) {
			if (r.message) {
				if (r.message.success) {
					frappe.msgprint({
						title: __("Connection Successful"),
						message: r.message.message,
						indicator: "green"
					});
				} else {
					frappe.msgprint({
						title: __("Connection Failed"),
						message: r.message.message,
						indicator: "red"
					});
				}
			}
		},
		error: function(r) {
			frappe.msgprint({
				title: __("Error"),
				message: __("Failed to test connection. Please try again."),
				indicator: "red"
			});
		}
	});
}
