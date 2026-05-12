app_name = "off_invoice_rebates"
app_title = "Off-Invoice Rebates"
app_publisher = "Lucsartech Srl"
app_description = "Gestione sconti fuori fattura per ERPNext V15 - calcolatori (scaglioni/volumi/target/forfettario), liquidazione (NC/compensazione/Payment Entry), politiche contabili configurabili"
app_email = "gianluca.simonini@lucsartech.it"
app_license = "gpl-3.0"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "off_invoice_rebates",
# 		"logo": "/assets/off_invoice_rebates/logo.png",
# 		"title": "Off-Invoice Rebates",
# 		"route": "/off_invoice_rebates",
# 		"has_permission": "off_invoice_rebates.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/off_invoice_rebates/css/off_invoice_rebates.css"
# app_include_js = "/assets/off_invoice_rebates/js/off_invoice_rebates.js"

# include js, css files in header of web template
# web_include_css = "/assets/off_invoice_rebates/css/off_invoice_rebates.css"
# web_include_js = "/assets/off_invoice_rebates/js/off_invoice_rebates.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "off_invoice_rebates/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "off_invoice_rebates/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "off_invoice_rebates.utils.jinja_methods",
# 	"filters": "off_invoice_rebates.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "off_invoice_rebates.install.before_install"
# after_install = "off_invoice_rebates.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "off_invoice_rebates.uninstall.before_uninstall"
# after_uninstall = "off_invoice_rebates.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "off_invoice_rebates.utils.before_app_install"
# after_app_install = "off_invoice_rebates.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "off_invoice_rebates.utils.before_app_uninstall"
# after_app_uninstall = "off_invoice_rebates.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "off_invoice_rebates.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"off_invoice_rebates.tasks.all"
# 	],
# 	"daily": [
# 		"off_invoice_rebates.tasks.daily"
# 	],
# 	"hourly": [
# 		"off_invoice_rebates.tasks.hourly"
# 	],
# 	"weekly": [
# 		"off_invoice_rebates.tasks.weekly"
# 	],
# 	"monthly": [
# 		"off_invoice_rebates.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "off_invoice_rebates.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "off_invoice_rebates.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "off_invoice_rebates.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["off_invoice_rebates.utils.before_request"]
# after_request = ["off_invoice_rebates.utils.after_request"]

# Job Events
# ----------
# before_job = ["off_invoice_rebates.utils.before_job"]
# after_job = ["off_invoice_rebates.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"off_invoice_rebates.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

