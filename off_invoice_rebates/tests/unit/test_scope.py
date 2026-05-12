# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Unit tests for ``rebate_engine.scope.build_scope_sql``.

These are SQL-string generation tests. The function uses ``frappe.db`` only
for the tree-descendants branch; tests without descendants stay DB-free.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(__file__)
_APP_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _APP_ROOT not in sys.path:
	sys.path.insert(0, _APP_ROOT)


class TestBuildScopeSql(unittest.TestCase):
	def setUp(self) -> None:
		try:
			from off_invoice_rebates.rebate_engine.scope import build_scope_sql
		except ModuleNotFoundError:
			self.skipTest("frappe not importable - run via bench instead")
		self.build_scope_sql = build_scope_sql

	def test_empty_filters_yield_empty_clause(self) -> None:
		sql, params = self.build_scope_sql([])
		self.assertEqual(sql, "")
		self.assertEqual(params, {})

	def test_filters_without_value_are_ignored(self) -> None:
		sql, params = self.build_scope_sql(
			[{"dimension": "item_group", "item_group": None, "include_descendants": 0}]
		)
		self.assertEqual(sql, "")
		self.assertEqual(params, {})

	def test_single_dimension_or_logic(self) -> None:
		sql, params = self.build_scope_sql(
			[
				{
					"dimension": "territory",
					"territory": "Italy",
					"include_descendants": 0,
				},
				{
					"dimension": "territory",
					"territory": "Spain",
					"include_descendants": 0,
				},
			]
		)
		# Same dimension -> OR between values, single AND group.
		self.assertIn("si.territory IN (", sql)
		self.assertNotIn(" AND ", sql)
		self.assertIn(" OR ", sql)
		self.assertEqual(set(params.values()), {"Italy", "Spain"})

	def test_distinct_dimensions_and_logic(self) -> None:
		sql, params = self.build_scope_sql(
			[
				{
					"dimension": "territory",
					"territory": "Italy",
					"include_descendants": 0,
				},
				{
					"dimension": "brand",
					"brand": "Acme",
					"include_descendants": 0,
				},
			]
		)
		self.assertIn(" AND ", sql)
		self.assertIn("si.territory IN (", sql)
		self.assertIn("item.brand", sql)
		self.assertEqual(set(params.values()), {"Italy", "Acme"})

	def test_unknown_dimension_raises(self) -> None:
		with self.assertRaises(ValueError):
			self.build_scope_sql(
				[{"dimension": "color", "color": "red", "include_descendants": 0}]
			)

	def test_tree_descendants_expansion(self) -> None:
		"""When include_descendants is set on a tree dimension, the values list
		is expanded via lft/rgt. We mock ``frappe.db`` to return three names
		and assert the IN-list grows accordingly.
		"""
		import off_invoice_rebates.rebate_engine.scope as scope_mod

		fake_db = mock.MagicMock()
		fake_db.get_value.return_value = 1  # lft
		# Two calls (lft + rgt) - patch both via side_effect.
		fake_db.get_value.side_effect = [1, 10]

		with (
			mock.patch.object(scope_mod, "frappe", create=True) as frappe_mod,
			mock.patch(
				"off_invoice_rebates.rebate_engine.scope.frappe.get_all",
				return_value=["A", "B", "C"],
				create=True,
			),
		):
			frappe_mod.db = fake_db
			frappe_mod.get_all.return_value = ["A", "B", "C"]
			sql, params = self.build_scope_sql(
				[
					{
						"dimension": "customer_group",
						"customer_group": "Wholesale",
						"include_descendants": 1,
					}
				]
			)
			# IN-list has three placeholders, one per expanded name.
			self.assertEqual(sql.count("%("), 3)
			self.assertEqual(
				sorted(params.values()),
				sorted(["A", "B", "C"]),
			)


if __name__ == "__main__":
	unittest.main()
