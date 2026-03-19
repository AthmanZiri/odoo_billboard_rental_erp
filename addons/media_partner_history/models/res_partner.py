from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    media_line_ids = fields.One2many('sale.order.line', 'partner_id', string='All Media Lines', domain=[('state', 'in', ['sale', 'done'])])
    
    billboard_line_ids = fields.Many2many('sale.order.line', string='Billboard History', compute='_compute_media_history_lines')
    digital_line_ids = fields.Many2many('sale.order.line', string='Digital History', compute='_compute_media_history_lines')
    canopy_line_ids = fields.Many2many('sale.order.line', string='Canopy History', compute='_compute_media_history_lines')
    printing_line_ids = fields.Many2many('sale.order.line', string='Printing History', compute='_compute_media_history_lines')

    billboard_count = fields.Integer(compute='_compute_media_history_lines', string='Billboards')
    digital_count = fields.Integer(compute='_compute_media_history_lines', string='Digital Slots')
    canopy_count = fields.Integer(compute='_compute_media_history_lines', string='Canopies')
    printing_count = fields.Integer(compute='_compute_media_history_lines', string='Printing')

    billboard_artwork_count = fields.Integer(compute='_compute_artwork_counts', string='Billboard Art')
    digital_artwork_count = fields.Integer(compute='_compute_artwork_counts', string='Digital Art')
    canopy_artwork_count = fields.Integer(compute='_compute_artwork_counts', string='Canopy Art')

    def _compute_media_history_lines(self):
        for partner in self:
            # We fetch all confirmed sale order lines for this partner
            # that have any of our media-related fields set.
            # Using order_id.partner_id for robustness if partner_id is not stored.
            all_lines = self.env['sale.order.line'].search([
                ('order_id.partner_id', '=', partner.id),
                ('state', 'in', ['sale', 'done']),
                '|', '|', '|',
                ('media_face_id', '!=', False),
                ('canopy_id', '!=', False),
                ('media_digital_screen_id', '!=', False),
                ('media_slot_id', '!=', False)
            ])

            billboard_lines = []
            digital_lines = []
            canopy_lines = []
            printing_lines = []

            for line in all_lines:
                if line.canopy_id:
                    canopy_lines.append(line.id)
                elif line.media_slot_id or (line.media_face_id and line.media_face_id.face_type == 'digital'):
                    digital_lines.append(line.id)
                elif line.media_face_id:
                    if 'flexi' in (line.media_face_id.name or '').lower():
                        printing_lines.append(line.id)
                    else:
                        billboard_lines.append(line.id)
                # Fallback check for printing products if any (future proofing)
                elif line.product_id and 'printing' in (line.product_id.name or '').lower():
                    printing_lines.append(line.id)

            partner.billboard_line_ids = [(6, 0, billboard_lines)]
            partner.digital_line_ids = [(6, 0, digital_lines)]
            partner.canopy_line_ids = [(6, 0, canopy_lines)]
            partner.printing_line_ids = [(6, 0, printing_lines)]
            
            partner.billboard_count = len(billboard_lines)
            partner.digital_count = len(digital_lines)
            partner.canopy_count = len(canopy_lines)
            partner.printing_count = len(printing_lines)

    def _compute_artwork_counts(self):
        for partner in self:
            hist = self.env['media.artwork.history'].search([('partner_id', '=', partner.id)])
            partner.billboard_artwork_count = len(hist.filtered(lambda h: h.site_category == 'billboard'))
            partner.digital_artwork_count = len(hist.filtered(lambda h: h.site_category == 'digital'))
            partner.canopy_artwork_count = len(hist.filtered(lambda h: h.site_category == 'canopy'))

    def action_view_billboard_history(self):
        view_id = self.env.ref('media_partner_history.view_sale_order_line_media_history_list').id
        return self._action_view_history(self.billboard_line_ids, _('Billboard History'), view_id=view_id)

    def action_view_digital_history(self):
        view_id = self.env.ref('media_partner_history.view_sale_order_line_media_history_list').id
        return self._action_view_history(self.digital_line_ids, _('Digital History'), view_id=view_id)

    def action_view_canopy_history(self):
        view_id = self.env.ref('media_partner_history.view_sale_order_line_media_history_list').id
        return self._action_view_history(self.canopy_line_ids, _('Canopy History'), view_id=view_id)

    def action_view_printing_history(self):
        return self._action_view_history(self.printing_line_ids, _('Printing History'))

    def action_view_billboard_artwork(self):
        return self._action_view_artwork('billboard', _('Billboard Artwork History'))

    def action_view_digital_artwork(self):
        return self._action_view_artwork('digital', _('Digital Artwork History'))

    def action_view_canopy_artwork(self):
        return self._action_view_artwork('canopy', _('Canopy Artwork History'))

    def _action_view_artwork(self, category, name):
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'media.artwork.history',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('site_category', '=', category)],
            'context': {'default_partner_id': self.id, 'default_site_category': category},
        }

    def _action_view_history(self, lines, name, view_id=False):
        action = {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', lines.ids)],
            'context': {'create': False},
        }
        if view_id:
            action['views'] = [(view_id, 'list'), (False, 'form')]
        return action
