// Copyright (c) 2026, Lucsartech Srl and contributors
// For license information, please see license.txt

frappe.query_reports["Rebate Liquidazioni in Corso"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Cliente"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "agreement",
			label: __("Accordo Premio"),
			fieldtype: "Link",
			options: "Rebate Agreement",
		},
		{
			fieldname: "status",
			label: __("Stato"),
			fieldtype: "Select",
			options: "\ndraft\ngenerated\nposted\ncancelled",
		},
		{
			fieldname: "settlement_mode",
			label: __("Modalita' Liquidazione"),
			fieldtype: "Select",
			options: "\ncredit_note\ninvoice_compensation\npayment_entry",
		},
		{
			fieldname: "from_date",
			label: __("Dal"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -6),
		},
		{
			fieldname: "to_date",
			label: __("Al"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
	],
};
