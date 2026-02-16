from odoo import models, fields

class MediaJobType(models.Model):
    _name = 'media.job.type'
    _description = 'Job Type'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
