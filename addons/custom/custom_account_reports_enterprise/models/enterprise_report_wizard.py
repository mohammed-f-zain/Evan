from odoo import _, api, fields, models


class EnterpriseAccountReportWizard(models.TransientModel):
    _name = "custom.enterprise.account.report.wizard"
    _description = "Enterprise-like Account Report Wizard"

    report_type = fields.Selection(
        [
            ("balance_sheet", "Balance Sheet"),
            ("profit_loss", "Profit and Loss"),
            ("trial_balance", "Trial Balance"),
            ("cash_flow", "Cash Flow"),
            ("executive_summary", "Executive Summary"),
            ("disallowed_expense", "Disallowed Expense"),
            ("loans_analysis", "Loans Analysis"),
            ("product_margins", "Product Margins"),
        ],
        required=True,
        default="balance_sheet",
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    date_from = fields.Date(required=True, default=lambda self: fields.Date.start_of(fields.Date.today(), "year"))
    date_to = fields.Date(required=True, default=fields.Date.today)
    line_ids = fields.One2many(
        "custom.enterprise.account.report.line", "wizard_id", string="Lines"
    )
    total_debit = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    total_credit = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    total_balance = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)

    @api.depends("line_ids.debit", "line_ids.credit", "line_ids.balance")
    def _compute_totals(self):
        for wizard in self:
            wizard.total_debit = sum(wizard.line_ids.mapped("debit"))
            wizard.total_credit = sum(wizard.line_ids.mapped("credit"))
            wizard.total_balance = sum(wizard.line_ids.mapped("balance"))

    def _account_type_filter(self):
        report_map = {
            "balance_sheet": (
                "asset_cash",
                "asset_current",
                "asset_fixed",
                "asset_non_current",
                "asset_prepayments",
                "asset_receivable",
                "liability_current",
                "liability_non_current",
                "liability_payable",
                "equity",
                "equity_unaffected",
            ),
            "profit_loss": (
                "income",
                "income_other",
                "expense",
                "expense_depreciation",
                "expense_direct_cost",
            ),
            "trial_balance": tuple(),
            "cash_flow": ("asset_cash",),
            "executive_summary": tuple(),
            "disallowed_expense": ("expense", "expense_depreciation", "expense_direct_cost"),
            "loans_analysis": ("liability_current", "liability_non_current", "liability_payable"),
            "product_margins": tuple(),
        }
        return report_map.get(self.report_type, tuple())

    def _get_name_expression(self):
        # Odoo stores translated names in JSONB in many databases.
        return "COALESCE(aa.name ->> 'en_US', aa.name ->> 'en', aa.name ->> 'ar_001', 'Account')"

    def _generate_standard_account_lines(self):
        account_types = self._account_type_filter()
        name_expr = self._get_name_expression()
        query = f"""
            SELECT
                aa.id AS account_id,
                aa.code_store ->> 'en_US' AS code,
                {name_expr} AS name,
                COALESCE(SUM(aml.debit), 0) AS debit,
                COALESCE(SUM(aml.credit), 0) AS credit,
                COALESCE(SUM(aml.balance), 0) AS balance
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE aml.company_id = %s
              AND aml.date >= %s
              AND aml.date <= %s
              AND aml.parent_state = 'posted'
              AND aml.display_type IS NULL
              AND aa.deprecated IS NOT TRUE
        """
        params = [self.company_id.id, self.date_from, self.date_to]
        if account_types:
            query += " AND aa.account_type = ANY(%s)"
            params.append(list(account_types))
        if self.report_type == "disallowed_expense":
            query += """
              AND (
                lower(COALESCE(aml.name, '')) LIKE '%disallow%'
                OR lower(COALESCE(aml.name, '')) LIKE '%non deductible%'
                OR lower(COALESCE(aml.name, '')) LIKE '%personal%'
                OR lower(COALESCE(aml.ref, '')) LIKE '%disallow%'
              )
            """
        if self.report_type == "loans_analysis":
            query += f"""
              AND (
                lower({name_expr}) LIKE '%loan%'
                OR lower({name_expr}) LIKE '%finance%'
                OR lower(COALESCE(aa.code_store ->> 'en_US', '')) LIKE '%loan%'
              )
            """
        query += """
            GROUP BY aa.id, aa.code_store, aa.name
            HAVING COALESCE(SUM(aml.debit), 0) != 0
                OR COALESCE(SUM(aml.credit), 0) != 0
                OR COALESCE(SUM(aml.balance), 0) != 0
            ORDER BY aa.code_store ->> 'en_US'
        """
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def _generate_executive_summary_lines(self):
        query = """
            SELECT
                COALESCE(SUM(CASE WHEN aa.account_type IN ('income', 'income_other') THEN -aml.balance ELSE 0 END), 0) AS revenue,
                COALESCE(SUM(CASE WHEN aa.account_type IN ('expense', 'expense_direct_cost', 'expense_depreciation') THEN aml.balance ELSE 0 END), 0) AS expenses,
                COALESCE(SUM(CASE WHEN aa.account_type LIKE 'asset%%' THEN aml.balance ELSE 0 END), 0) AS assets,
                COALESCE(SUM(CASE WHEN aa.account_type LIKE 'liability%%' THEN -aml.balance ELSE 0 END), 0) AS liabilities,
                COALESCE(SUM(CASE WHEN aa.account_type LIKE 'equity%%' THEN -aml.balance ELSE 0 END), 0) AS equity
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE aml.company_id = %s
              AND aml.date >= %s
              AND aml.date <= %s
              AND aml.parent_state = 'posted'
              AND aml.display_type IS NULL
              AND aa.deprecated IS NOT TRUE
        """
        self.env.cr.execute(query, [self.company_id.id, self.date_from, self.date_to])
        row = self.env.cr.dictfetchone() or {}
        revenue = row.get("revenue", 0.0)
        expenses = row.get("expenses", 0.0)
        net_profit = revenue - expenses
        assets = row.get("assets", 0.0)
        liabilities = row.get("liabilities", 0.0)
        equity = row.get("equity", 0.0)
        return [
            {"account_id": False, "code": "REV", "name": _("Revenue"), "debit": 0.0, "credit": 0.0, "balance": revenue},
            {"account_id": False, "code": "EXP", "name": _("Expenses"), "debit": 0.0, "credit": 0.0, "balance": expenses},
            {"account_id": False, "code": "NP", "name": _("Net Profit"), "debit": 0.0, "credit": 0.0, "balance": net_profit},
            {"account_id": False, "code": "AST", "name": _("Total Assets"), "debit": 0.0, "credit": 0.0, "balance": assets},
            {"account_id": False, "code": "LIA", "name": _("Total Liabilities"), "debit": 0.0, "credit": 0.0, "balance": liabilities},
            {"account_id": False, "code": "EQT", "name": _("Total Equity"), "debit": 0.0, "credit": 0.0, "balance": equity},
        ]

    def _generate_product_margin_lines(self):
        query = """
            SELECT
                pt.id AS product_tmpl_id,
                pp.default_code AS code,
                COALESCE(pt.name ->> 'en_US', pt.name ->> 'en', pt.name ->> 'ar_001', 'Product') AS name,
                COALESCE(SUM(CASE WHEN aa.account_type IN ('income', 'income_other') THEN -aml.balance ELSE 0 END), 0) AS revenue,
                COALESCE(SUM(CASE WHEN aa.account_type IN ('expense_direct_cost', 'expense') THEN aml.balance ELSE 0 END), 0) AS cost
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            JOIN product_product pp ON pp.id = aml.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE aml.company_id = %s
              AND aml.date >= %s
              AND aml.date <= %s
              AND aml.parent_state = 'posted'
              AND aml.display_type IS NULL
              AND aml.product_id IS NOT NULL
            GROUP BY pt.id, pp.default_code, pt.name
            HAVING COALESCE(SUM(CASE WHEN aa.account_type IN ('income', 'income_other') THEN -aml.balance ELSE 0 END), 0) != 0
               OR COALESCE(SUM(CASE WHEN aa.account_type IN ('expense_direct_cost', 'expense') THEN aml.balance ELSE 0 END), 0) != 0
            ORDER BY pp.default_code, pt.id
        """
        self.env.cr.execute(query, [self.company_id.id, self.date_from, self.date_to])
        rows = self.env.cr.dictfetchall()
        result = []
        for row in rows:
            revenue = row.get("revenue", 0.0) or 0.0
            cost = row.get("cost", 0.0) or 0.0
            margin = revenue - cost
            result.append(
                {
                    "account_id": False,
                    "code": row.get("code") or f"P{row.get('product_tmpl_id')}",
                    "name": row.get("name") or _("Product"),
                    "debit": cost,
                    "credit": revenue,
                    "balance": margin,
                }
            )
        return result

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        if self.report_type == "executive_summary":
            rows = self._generate_executive_summary_lines()
        elif self.report_type == "product_margins":
            rows = self._generate_product_margin_lines()
        else:
            rows = self._generate_standard_account_lines()

        line_values = [
            {
                "wizard_id": self.id,
                "account_id": row["account_id"],
                "code": row["code"] or "",
                "name": row["name"] or _("Account"),
                "debit": row["debit"] or 0.0,
                "credit": row["credit"] or 0.0,
                "balance": row["balance"] or 0.0,
            }
            for row in rows
        ]
        if line_values:
            self.env["custom.enterprise.account.report.line"].create(line_values)

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }


class EnterpriseAccountReportLine(models.TransientModel):
    _name = "custom.enterprise.account.report.line"
    _description = "Enterprise-like Account Report Line"
    _order = "code, id"

    wizard_id = fields.Many2one("custom.enterprise.account.report.wizard", required=True, ondelete="cascade")
    account_id = fields.Many2one("account.account", readonly=True)
    code = fields.Char(readonly=True)
    name = fields.Char(readonly=True)
    debit = fields.Monetary(readonly=True, currency_field="currency_id")
    credit = fields.Monetary(readonly=True, currency_field="currency_id")
    balance = fields.Monetary(readonly=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="wizard_id.company_id.currency_id", readonly=True)

