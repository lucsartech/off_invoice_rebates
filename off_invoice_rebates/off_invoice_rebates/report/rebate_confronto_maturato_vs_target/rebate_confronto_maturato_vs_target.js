// Copyright (c) 2026, Lucsartech Srl and contributors
// For license information, please see license.txt

frappe.query_reports["Rebate Confronto Maturato vs Target"] = {
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
			label: __("Periodo Dal"),
			fieldtype: "Date",
			default: frappe.datetime.year_start(),
		},
		{
			fieldname: "to_date",
			label: __("Periodo Al"),
			fieldtype: "Date",
			default: frappe.datetime.year_end(),
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "achievement_percent" && data) {
			const pct = data.achievement_percent || 0;
			if (pct >= 100) {
				value = `<span style="color: var(--green-600); font-weight: 600">${value}</span>`;
			} else if (pct >= 75) {
				value = `<span style="color: var(--orange-600)">${value}</span>`;
			} else {
				value = `<span style="color: var(--red-600)">${value}</span>`;
			}
		}
		return value;
	},
};
