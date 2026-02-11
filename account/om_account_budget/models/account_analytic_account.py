from odoo import fields, models, api
from odoo.tools import Query


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    crossovered_budget_line = fields.One2many(
        'crossovered.budget.lines', 'analytic_account_id', 'Budget Lines'
    )


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _where_calc(self, domain, active_test=True):
        """Computes the WHERE clause needed to implement an OpenERP domain.

        :param list domain: the domain to compute
        :param bool active_test: whether the default filtering of records with
            ``active`` field set to ``False`` should be applied.
        :return: the query expressing the given domain as provided in domain
        :rtype: Query
        """
        # if the object has an active field ('active', 'x_active'), filter out all
        # inactive records unless they were explicitly asked for
        if domain:
            return self.with_context(active_test=active_test)._search(domain)
        else:
            return Query(self.env, self._table, self._table_sql)

