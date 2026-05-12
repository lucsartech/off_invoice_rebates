// Copyright (c) 2026, Lucsartech Srl and contributors
// For license information, please see license.txt

frappe.query_reports["Rebate Riconciliazione Contabile"] = {
	filters: [
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
			label: __("Stato Liquidazione"),
			fieldtype: "Select",
			options: "\ndraft\ngenerated\nposted\ncancelled",
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "reconciliation_status" && data) {
			const status = data.reconciliation_status || "";
			if (status === __("Riconciliato")) {
				value = `<span style="color: var(--green-600)">${value}</span>`;
			} else if (status.indexOf("MANCANTE") === 0 || status === __("MANCANTE - scrittura attesa non collegata")) {
				value = `<span style="color: var(--red-600); font-weight: 600">${value}</span>`;
			} else if (status === __("Differenza")) {
				value = `<span style="color: var(--orange-600)">${value}</span>`;
			}
		}
		return value;
	},
};
