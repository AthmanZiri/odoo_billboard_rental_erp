from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMultiPaymentLine(models.Model):
    _name = 'account.multi.payment.line'
    _description = 'Multi Invoice Payment Line'

    multi_payment_id = fields.Many2one('account.multi.payment', string='Multi Payment', ondelete='cascade')
    move_id = fields.Many2one('account.move', string='Invoice/Bill', required=True, domain="[('partner_id', '=', partner_id), ('state', '=', 'posted'), ('payment_state', 'in', ('not_paid', 'partial'))]")
    partner_id = fields.Many2one('res.partner', related='multi_payment_id.partner_id')
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id')
    amount_total = fields.Monetary(string='Total Amount', related='move_id.amount_total')
    amount_residual = fields.Monetary(string='Amount Due', related='move_id.amount_residual')
    amount_payment = fields.Monetary(string='Payment Amount', currency_field='currency_id')

    @api.onchange('move_id')
    def _onchange_move_id(self):
        if self.move_id:
            self.amount_payment = self.amount_residual

class AccountMultiPayment(models.Model):
    _name = 'account.multi.payment'
    _description = 'Multi Invoice Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Payment Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Payment Type', required=True, default='inbound')
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], string='Partner Type', required=True, default='customer')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, tracking=True)
    journal_id = fields.Many2one('account.journal', string='Payment Method', required=True, domain="[('type', 'in', ('bank', 'cash'))]")
    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, tracking=True)
    communication = fields.Char(string='Memo')
    amount = fields.Monetary(string='Amount to Pay', currency_field='currency_id', help="Total amount the customer/vendor is paying.")
    total_residual_amount = fields.Monetary(string='Total Open Amount', compute='_compute_total_residual', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    line_ids = fields.One2many('account.multi.payment.line', 'multi_payment_id', string='Payment Lines')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('line_ids.amount_residual')
    def _compute_total_residual(self):
        for payment in self:
            payment.total_residual_amount = sum(payment.line_ids.mapped('amount_residual'))

    @api.onchange('partner_id', 'payment_type')
    def _onchange_partner_payment_type(self):
        if not self.partner_id or not self.payment_type:
            self.line_ids = [(5, 0, 0)]
            return

        # Determine move types based on payment type
        if self.payment_type == 'inbound':
            move_types = ['out_invoice', 'out_refund']
        else:
            move_types = ['in_invoice', 'in_refund']

        # Search for open invoices/bills, ordered by date (FIFO)
        moves = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', 'in', move_types),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ], order='invoice_date asc, id asc')

        # Prepare line values
        line_vals = []
        for move in moves:
            line_vals.append((0, 0, {
                'move_id': move.id,
                'amount_payment': 0.0, # Reset to 0, will be filled by amount distribution
            }))

        self.line_ids = [(5, 0, 0)] + line_vals
        # Trigger distribution if amount is already set
        if self.amount:
            self._onchange_amount()

    @api.onchange('amount')
    def _onchange_amount(self):
        """ FIFO Distribution of payment amount """
        remaining_amount = self.amount
        for line in self.line_ids:
            if remaining_amount > 0:
                allocation = min(remaining_amount, line.amount_residual)
                line.amount_payment = allocation
                remaining_amount -= allocation
            else:
                line.amount_payment = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('account.multi.payment') or _('New')
        return super(AccountMultiPayment, self).create(vals_list)

    def action_post(self):
        for payment in self:
            if not payment.line_ids:
                raise UserError(_("You must add at least one line to process payment."))
            
            for line in payment.line_ids:
                if line.amount_payment <= 0:
                    continue
                
                # Create account.payment for each line
                payment_vals = {
                    'payment_type': payment.payment_type,
                    'partner_type': payment.partner_type,
                    'partner_id': payment.partner_id.id,
                    'journal_id': payment.journal_id.id,
                    'amount': line.amount_payment,
                    'date': payment.payment_date,
                    'memo': payment.communication or payment.name,
                    'currency_id': payment.currency_id.id,
                    'payment_method_line_id': payment.journal_id.inbound_payment_method_line_ids[0].id if payment.payment_type == 'inbound' else payment.journal_id.outbound_payment_method_line_ids[0].id,
                }
                
                new_payment = self.env['account.payment'].create(payment_vals)
                new_payment.action_post()
                
                # Reconcile with invoice
                line_to_reconcile = new_payment.move_id.line_ids.filtered(lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
                invoice_line = line.move_id.line_ids.filtered(lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
                (line_to_reconcile + invoice_line).reconcile()
                
            payment.write({'state': 'posted'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})
