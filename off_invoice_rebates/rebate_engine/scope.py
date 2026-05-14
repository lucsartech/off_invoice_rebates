# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

# Dimensioni gerarchiche → DocType corrispondente
_TREE_DOCTYPES = {
	"item_group": "Item Group",
	"territory": "Territory",
	"customer_group": "Customer Group",
}


def build_scope_sql(scope_filters: list[dict]) -> tuple[str, dict]:
	"""Costruisce (sql_fragment, params) per filtrare Sales Invoice / Sales Invoice Item.

	Conventions del chiamante:
	- alias `si` su `tabSales Invoice`
	- alias `sii` su `tabSales Invoice Item`

	Regola: AND fra dimensioni distinte, OR fra valori della stessa dimensione.
	"""
	if not scope_filters:
		return "", {}

	groups: dict[str, list[tuple[str, object]]] = {}
	for row in scope_filters:
		dim = row.get("dimension")
		if not dim:
			continue
		val = row.get(dim)
		if not val:
			continue
		groups.setdefault(dim, []).append((val, row.get("include_descendants")))

	if not groups:
		return "", {}

	where_parts: list[str] = []
	params: dict = {}
	counter = 0

	for dim, values in groups.items():
		sub_parts: list[str] = []
		for val, include_desc in values:
			counter += 1
			names = _expand_with_descendants(dim, val, include_desc)
			placeholders = []
			for i, n in enumerate(names):
				pkey = f"scope_{dim}_{counter}_{i}"
				params[pkey] = n
				placeholders.append(f"%({pkey})s")
			column = _sql_column_for_dim(dim)
			sub_parts.append(f"{column} IN ({', '.join(placeholders)})")
		where_parts.append("(" + " OR ".join(sub_parts) + ")")

	return " AND ".join(where_parts), params


def _sql_column_for_dim(dim: str) -> str:
	mapping = {
		"item_group": ("(SELECT item.item_group FROM `tabItem` item WHERE item.name = sii.item_code)"),
		"brand": ("(SELECT item.brand FROM `tabItem` item WHERE item.name = sii.item_code)"),
		"territory": "si.territory",
		"customer_group": ("(SELECT c.customer_group FROM `tabCustomer` c WHERE c.name = si.customer)"),
	}
	if dim not in mapping:
		raise ValueError(f"Dimensione di perimetro non gestita: {dim}")
	return mapping[dim]


def _expand_with_descendants(dim: str, parent: str, include_desc) -> list[str]:
	if not include_desc or dim not in _TREE_DOCTYPES:
		return [parent]
	dt = _TREE_DOCTYPES[dim]
	lft = frappe.db.get_value(dt, parent, "lft")
	rgt = frappe.db.get_value(dt, parent, "rgt")
	if lft is None or rgt is None:
		return [parent]
	descendants = frappe.get_all(
		dt,
		filters={"lft": (">=", lft), "rgt": ("<=", rgt)},
		pluck="name",
	)
	return descendants or [parent]
