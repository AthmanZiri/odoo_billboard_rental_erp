from odoo import models, fields, api, _

class MediaRentalWizard(models.TransientModel):
    _name = 'media.rental.wizard'
    _description = 'Select Billboards for Rental'

    rental_id = fields.Many2one('media.rental', string='Rental', required=True)
    start_date = fields.Date(related='rental_id.start_date')
    end_date = fields.Date(related='rental_id.end_date')
    available_face_ids = fields.Many2many('media.face', string='Available Billboards', 
                                         domain="[('id', 'in', available_faces_domain)]")
    
    available_faces_domain = fields.Many2many('media.face', compute='_compute_available_faces_domain')

    @api.depends('start_date', 'end_date')
    def _compute_available_faces_domain(self):
        for wizard in self:
            if not wizard.start_date or not wizard.end_date:
                wizard.available_faces_domain = self.env['media.face'].search([])
                continue
            
            # Use the same logic as in media.rental to find available faces
            booked_lines = self.env['sale.order.line'].search([
                ('media_face_id', '!=', False),
                ('state', 'in', ['sale', 'done']),
                ('start_date', '<=', wizard.end_date),
                ('end_date', '>=', wizard.start_date),
            ])
            booked_face_ids = booked_lines.mapped('media_face_id').ids
            wizard.available_faces_domain = self.env['media.face'].search([('id', 'not in', booked_face_ids)])

    def action_add_billboards(self):
        self.ensure_one()
        rental_lines = []
        for face in self.available_face_ids:
            rental_lines.append((0, 0, {
                'rental_id': self.rental_id.id,
                'face_id': face.id,
                'price_unit': face.price_per_month,
            }))
        self.rental_id.write({'rental_line_ids': rental_lines})
        return {'type': 'ir.actions.act_window_close'}
