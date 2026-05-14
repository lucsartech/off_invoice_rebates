# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

# Import the calculator modules so the @register decorators run on package load.
from off_invoice_rebates.rebate_engine.calculators import (
	flat_contribution,
	target_growth,
	turnover_tiered,
	volume,
)
