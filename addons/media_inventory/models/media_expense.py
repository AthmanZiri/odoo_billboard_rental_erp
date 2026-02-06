from odoo import models, fields, api

class MediaExpense(models.Model):
    _name = 'media.expense'
    _description = 'Media Asset Expense'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Description', required=True)
    site_id = fields.Many2one('media.site', string='Site')
    media_face_id = fields.Many2one('media.face', string='Face', domain="[('site_id', '=', site_id)]")
    
    date = fields.Date(string='Date', default=fields.Date.today)
    amount = fields.Float(string='Amount', required=True)
    
    category = fields.Selection([
        ('furniture', 'Furniture'),
        ('pipes', 'Pipes'),
        ('maintenance', 'Maintenance'),
        ('installation', 'Installation'),
        ('repair', 'Repair'),
        ('other', 'Other')
    ], string='Category', required=True, default='other')
    
    expense_file = fields.Binary(string='Receipt/Attachment')
    expense_filename = fields.Char(string='Attachment Filename')
    
    notes = fields.Text(string='Notes')

    @api.onchange('media_face_id')
    def _onchange_media_face_id(self):
        if self.media_face_id and not self.site_id:
            self.site_id = self.media_face_id.site_id.id
