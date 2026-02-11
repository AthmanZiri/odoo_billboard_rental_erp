from odoo import models, fields, api, _

class MediaArtworkHistory(models.Model):
    _name = 'media.artwork.history'
    _description = 'Artwork History'
    _order = 'upload_date desc'

    face_id = fields.Many2one('media.face', string='Face', required=True, ondelete='cascade')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Contract Line', ondelete='set null')
    
    artwork_file = fields.Image(string='Artwork', required=True)
    artwork_filename = fields.Char(string='Filename')
    
    upload_date = fields.Datetime(string='Upload Date', default=fields.Datetime.now, readonly=True)
    description = fields.Text(string='Description')
    uploaded_by = fields.Many2one('res.users', string='Uploaded By', default=lambda self: self.env.user, readonly=True)

    def name_get(self):
        result = []
        for record in self:
            name = f"Artwork on {record.upload_date.strftime('%Y-%m-%d %H:%M')}"
            result.append((record.id, name))
        return result
