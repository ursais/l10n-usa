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
                    discount = line.discount_amount
                    payment_difference = line.payment_difference
                    writeoff = 0.0
                    invoice_close = False
                    if payment_difference:
                        writeoff = (
                            payment_difference and payment_difference - discount or 0.0
                        )
                        invoice_close = line.payment_difference_handling != "open"
                    use_debit = line.move_id.move_type in (
                        "in_invoice",
                        "out_refund",
                    )
                    temp_vals["move_id"] = line.move_id.id
                    if use_debit:
                        temp_vals["debit"] = amount + discount
                    else:
                        temp_vals["credit"] = amount + discount

                    line_ids.append((0, 0, temp_vals))

                    if discount > 0:
                        if payment_difference:
                            discount_information = line.move_id.invoice_payment_term_id._check_payment_term_discount(
                                line.move_id, line.date
                            )
                            discount_vals = temp_vals.copy()
                            discount_vals["account_id"] = discount_information[1]
                            discount_vals["name"] = "Early Pay Discount"
                            if use_debit:
                                discount_vals["debit"] = 0.0
                                discount_vals["credit"] = discount_information[0]
                            else:
                                discount_vals["credit"] = 0.0
                                discount_vals["debit"] = discount_information[0]
                            discount_vals["bank_payment_line_id"] = False
                            if discount_vals:
                                line_ids.append((0, 0, discount_vals))
                            # Discount Taken Update
                            line.move_id.discount_taken = discount
                        else:
                            #Case: If user Manually enters discount amount
                            discount_vals = temp_vals.copy()
                            discount_vals["account_id"] = line.writeoff_account_id and line.writeoff_account_id.id or False
                            discount_vals["name"] = "Early Pay Discount"
                            if use_debit:
                                discount_vals["debit"] = 0.0
                                discount_vals["credit"] = discount
                            else:
                                discount_vals["credit"] = 0.0
                                discount_vals["debit"] = discount
                            discount_vals["bank_payment_line_id"] = False
                            if discount_vals:
                                line_ids.append((0, 0, discount_vals))
                            # Discount Taken Update
                            line.move_id.discount_taken = discount

                    if invoice_close and round(writeoff, 2):
                        if use_debit:
                            temp_vals["debit"] = amount + discount + round(writeoff, 2)
                        else:
                            temp_vals["credit"] = amount + discount + round(writeoff, 2)
                        writeoff_vals = line.move_id._prepare_writeoff_move_line(
                            line, temp_vals.copy()
                        )
                        writeoff_vals["bank_payment_line_id"] = False
                        if writeoff_vals:
                            line_ids.append((0, 0, writeoff_vals))
            # payment order line
            else:
                line_ids.append(vals)
        if line_ids:
            line_ids = self._prepare_ach_payment_move(values)
        values["line_ids"] = line_ids
        return values

    def _prepare_ach_payment_move(self,values):
        bank_payment_line_obj = self.env["bank.payment.line"]
        line_vals = []
        for vals in values.get("line_ids"):
            if "bank_payment_line_id" in vals[2] and vals[2]["bank_payment_line_id"]:
                bank_payment_id = vals[2].get("bank_payment_line_id")
                account_bank_payment = bank_payment_line_obj.browse(bank_payment_id)
                for payment_line in account_bank_payment.payment_line_ids:
                    temp_vals = vals[2].copy()
                    amount = payment_line.amount_currency
                    total_amount = payment_line.total_amount
                    amount_difference = round((total_amount - amount), 2)
                    payment_difference = amount_difference
                    writeoff = payment_difference or 0.0
                    invoice_close = payment_line.payment_difference_handling != "open"
                    use_debit = payment_line.move_id.move_type in (
                        "in_invoice",
                        "out_refund",
                    )
                    temp_vals["move_id"] = payment_line.move_id.id
                    if use_debit:
                        temp_vals["debit"] = total_amount - payment_difference
                    else:
                        temp_vals["credit"] = total_amount - payment_difference
                    line_vals.append((0, 0, temp_vals))
                    if invoice_close:
                        if use_debit:
                            temp_vals["debit"] = amount + payment_difference
                        else:
                            temp_vals["credit"] = amount + payment_difference
                        if round(writeoff, 2):
                            writeoff_vals = payment_line.move_id._prepare_writeoff_move_line(payment_line, temp_vals.copy())
                            writeoff_vals["bank_payment_line_id"] = False
                            if writeoff_vals:
                                line_vals.append((0, 0, writeoff_vals))
            else:
                line_vals.append(vals)
        return line_vals
