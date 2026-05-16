from odoo import models


class AccountReport(models.Model):
    """
    Keep the core Odoo `account.report` model intact.
    We only extend it (no field/method override) to avoid losing built-in
    methods like `_create_menu_item_for_report`.
    """

    _inherit = "account.report"

