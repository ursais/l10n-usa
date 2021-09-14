# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def _prepare_move(self, bank_lines=None):
        values = super()._prepare_move(bank_lines)
        bank_payment_line_pool = self.env["bank.payment.line"]
        line_ids = []
        for vals in values.get("line_ids"):
            # get the debit line for adjusting A/P entries
            if "bank_payment_line_id" in vals[2] and vals[2]["bank_payment_line_id"]:
                bank_payment_id = vals[2].get("bank_payment_line_id")
                bank_payment = bank_payment_line_pool.browse(bank_payment_id)
                for line in bank_payment.payment_line_ids:

                    temp_vals = vals[2].copy()
                    amount = line.amount_currency
                    total_amount = line.total_amount
                    amount_difference = round((total_amount - amount), 2)
                    payment_difference = amount_difference
                    writeoff = payment_difference or 0.0
                    invoice_close = line.payment_difference_handling != "open"
                    use_debit = line.move_id.move_type in (
                        "in_invoice",
                        "out_refund",
                    )
                    temp_vals["move_id"] = line.move_id.id
                    if use_debit:
                        temp_vals["debit"] = total_amount - payment_difference
                    else:
                        temp_vals["credit"] = total_amount - payment_difference

                    line_ids.append((0, 0, temp_vals))

                    if invoice_close:
                        if use_debit:
                            temp_vals["debit"] = amount + payment_difference
                        else:
                            temp_vals["credit"] = amount + payment_difference
                        if round(writeoff, 2):
                            writeoff_vals = line.move_id._prepare_writeoff_move_line(
                                line, temp_vals.copy()
                            )
                            writeoff_vals["bank_payment_line_id"] = False
                            if writeoff_vals:
                                line_ids.append((0, 0, writeoff_vals))
            # payment order line
            else:
                line_ids.append(vals)
        values["line_ids"] = line_ids
        return values
