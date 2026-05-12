# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


class RebateEngineError(frappe.ValidationError):
	pass


class RebatePeriodLocked(RebateEngineError):
	pass


class UnknownCalculator(RebateEngineError):
	pass


class InvalidTierConfiguration(RebateEngineError):
	pass


class NoTransactionsInScope(RebateEngineError):
	pass
