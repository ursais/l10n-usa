# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_onpay_id = fields.Many2one(
        "onpay.pay.type",
        string="OnPay Type",
    )
