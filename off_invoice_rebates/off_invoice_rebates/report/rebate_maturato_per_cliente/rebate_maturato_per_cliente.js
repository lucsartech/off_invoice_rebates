// Copyright (c) 2026, Lucsartech Srl and contributors
// For license information, please see license.txt

frappe.query_reports["Rebate Maturato per Cliente"] = {
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
		{
			fieldname: "settlement_status",
			label: __("Stato Liquidazione"),
			fieldtype: "Select",
			options: "\nunsettled\npartial\nsettled",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "residual" && data && data.residual > 0) {
			value = `<span style="color: var(--orange-600)">${value}</span>`;
		}
		return value;
	},
};
