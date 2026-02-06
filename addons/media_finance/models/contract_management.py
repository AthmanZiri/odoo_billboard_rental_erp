from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoiced_months = fields.Char(string='Invoiced Months', help='Comma separated YYYY-MM of invoiced months')

    def action_cancel(self):
        # Cancel draft invoices related to this sale order when contract is cancelled
        res = super(SaleOrder, self).action_cancel()
        for order in self:
            draft_invoices = self.env['account.move'].search([
                ('invoice_origin', '=', order.name),
                ('state', '=', 'draft')
            ])
            if draft_invoices:
                draft_invoices.button_cancel()
        return res

    def _cron_generate_monthly_invoices(self):
        today = fields.Date.today()
        current_month = today.strftime('%Y-%m')
        
        # Search for active rental contracts
        orders = self.search([
            ('state', '=', 'sale'),
            ('lease_start_date', '<=', today),
            ('lease_end_date', '>=', today),
        ])
        
        for order in orders:
            invoiced = (order.invoiced_months or '').split(',')
            if current_month not in invoiced:
                # Generate draft invoice for the current month
                order._create_monthly_invoice(today)
                
                # Mark as invoiced
                invoiced.append(current_month)
                order.invoiced_months = ','.join(filter(None, invoiced))

    def _cron_contract_expiry_reminder(self):
        today = fields.Date.today()
        # Notify for contracts ending in 5, 7, 15, and 30 days
        reminder_days = [5, 7, 15, 30]
        for days in reminder_days:
            expiry_date = today + relativedelta(days=days)
            orders = self.search([
                ('state', '=', 'sale'),
                ('lease_end_date', '=', expiry_date)
            ])
            for order in orders:
                order._notify_contract_expiry(days)

    def _notify_contract_expiry(self, days):
        self.ensure_one()
        # In a real system, send email or push notification
        # For now, we'll log it or use the chatter
        self.message_post(body=_("Contract for %s is expiring in %s days on %s.") % (self.name, days, self.lease_end_date))

    def _create_monthly_invoice(self, date):
        self.ensure_one()
        # Simple logic to create a draft invoice for the current month
        # In a real scenario, this would use the standard _create_invoices() 
        # but with filtered lines or modified quantities for the period.
        # For this prototype, we'll assume the full month is invoiced.
        invoice = self._create_invoices(final=False)
        invoice.invoice_date = date
        return invoice

class MediaSite(models.Model):
    _inherit = 'media.site'

    pending_invoice_count = fields.Integer(compute='_compute_pending_invoices', store=True, group_operator="sum")
    unpaid_invoices_amount = fields.Float(compute='_compute_pending_invoices', string='Total Unpaid Amount', store=True, group_operator="sum")
    occupancy_rate = fields.Float(compute='_compute_occupancy_rate', string='Occupancy Rate (%)', store=True, group_operator="avg")

    @api.depends('total_faces_count', 'occupied_faces_count')
    def _compute_occupancy_rate(self):
        for site in self:
            site.occupancy_rate = (site.occupied_faces_count / site.total_faces_count * 100.0) if site.total_faces_count else 0.0

    @api.depends('face_ids')
    def _compute_pending_invoices(self):
        for site in self:
            # Count unpaid invoices (posted and not paid) related to faces on this site
            face_ids = site.face_ids.ids
            invoice_lines = self.env['account.move.line'].search([
                ('media_face_id', 'in', face_ids),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
                ('move_id.payment_state', 'in', ['not_paid', 'partial'])
            ])
            invoices = invoice_lines.mapped('move_id')
            site.pending_invoice_count = len(invoices)
            site.unpaid_invoices_amount = sum(invoices.mapped('amount_residual'))

    def action_view_pending_invoices(self):
        self.ensure_one()
        face_ids = self.face_ids.ids
        invoices = self.env['account.move.line'].search([
            ('media_face_id', 'in', face_ids),
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '=', 'posted'),
            ('move_id.payment_state', 'in', ['not_paid', 'partial'])
        ]).mapped('move_id')
        
        return {
            'name': _('Pending Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {'create': False},
        }
