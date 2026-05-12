# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Unit tests for ``settlement.iva.resolve``.

The resolver maps ``(iva_regime, settlement_mode)`` to an ``IvaResolution``
dataclass. Pure logic - no Frappe DB calls when the regime is valid.
"""

from __future__ import annotations

import os
import sys
import types
import unittest

_HERE = os.path.dirname(__file__)
_APP_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _APP_ROOT not in sys.path:
	sys.path.insert(0, _APP_ROOT)


class _FakeSettlement(types.SimpleNamespace):
	pass


class TestIvaResolver(unittest.TestCase):
	def setUp(self) -> None:
		try:
			from off_invoice_rebates.settlement.iva import resolve
		except ModuleNotFoundError:
			self.skipTest("frappe not importable - run via bench instead")
		self.resolve = resolve

	def test_in_natura_credit_note(self) -> None:
		s = _FakeSettlement(iva_regime="in_natura", settlement_mode="credit_note")
		r = self.resolve(s)
		self.assertEqual(r.regime, "in_natura")
		self.assertTrue(r.generates_credit_note)
		self.assertTrue(r.needs_return_against)

	def test_fuori_campo_credit_note(self) -> None:
		s = _FakeSettlement(iva_regime="fuori_campo", settlement_mode="credit_note")
		r = self.resolve(s)
		self.assertEqual(r.regime, "fuori_campo")
		self.assertTrue(r.generates_credit_note)
		self.assertFalse(r.needs_return_against)

	def test_fuori_campo_payment_entry_does_not_generate_nc(self) -> None:
		s = _FakeSettlement(iva_regime="fuori_campo", settlement_mode="payment_entry")
		r = self.resolve(s)
		self.assertFalse(r.generates_credit_note)
		self.assertFalse(r.needs_return_against)


if __name__ == "__main__":
	unittest.main()
