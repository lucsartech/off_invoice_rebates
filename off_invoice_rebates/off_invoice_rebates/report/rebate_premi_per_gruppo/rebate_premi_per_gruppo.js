// Copyright (c) 2026, Lucsartech Srl and contributors
// For license information, please see license.txt

frappe.query_reports["Rebate Premi per Gruppo"] = {
	filters: [
		{
			fieldname: "dimension",
			label: __("Dimensione Perimetro"),
			fieldtype: "Select",
			options: "item_group\nbrand\nterritory\ncustomer_group",
			default: "item_group",
			reqd: 1,
		},
		{
			fieldname: "agreement",
			label: __("Accordo Premio"),
			fieldtype: "Link",
			options: "Rebate Agreement",
		},
		{
			fieldname: "customer",
			label: __("Cliente"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "from_date",
			label: __("Dal"),
			fieldtype: "Date",
			default: frappe.datetime.year_start(),
		},
		{
			fieldname: "to_date",
			label: __("Al"),
			fieldtype: "Date",
			default: frappe.datetime.year_end(),
		},
	],
};
