# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""F4 accounting policies for OffInvoiceRebates.

Importing the package side-effect-registers all built-in policies
(``full_accrual``, ``on_settlement``, ``memo_only``) into the registry in
:mod:`off_invoice_rebates.accounting.base`.
"""

from off_invoice_rebates.accounting import full_accrual, memo_only, on_settlement
