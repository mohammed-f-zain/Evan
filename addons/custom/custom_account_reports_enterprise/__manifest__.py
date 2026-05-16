{
    "name": "Custom Account Reports Enterprise",
    "version": "18.0.1.0",
    "category": "Accounting/Reporting",
    "summary": "Enterprise-like accounting reporting dashboards",
    "depends": ["account", "web", "base_accounting_kit", "base_account_budget"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_report_views.xml",
        "views/enterprise_report_wizard_views.xml",
        "views/account_report_menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}

