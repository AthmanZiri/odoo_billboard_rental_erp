from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    media_face_id = fields.One2many('media.face', 'product_id', string='Media Faces')

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            # Search for faces or sites matching the name
            face_domain = [
                '|', '|', '|',
                ('name', operator, name),
                ('code', operator, name),
                ('site_id.name', operator, name),
                ('site_id.code', operator, name)
            ]
            faces = self.env['media.face'].search(face_domain)
            if faces:
                product_ids = faces.mapped('product_id').ids
                if product_ids:
                    # Search for products that match normal criteria OR are linked to matching faces
                    domain = ['|', ('id', 'in', product_ids)] + domain
        
        return super(ProductProduct, self)._name_search(name, domain, operator, limit, order)
