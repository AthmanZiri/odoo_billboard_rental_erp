from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    media_face_id = fields.Many2one('media.face', string='Media Face')
    media_digital_screen_id = fields.Many2one('media.digital.screen', string='Digital Screen')
    canopy_id = fields.Many2one('media.canopy', string='Canopy')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    
    artwork_file = fields.Image(string='Artwork/Graphic', max_width=1920, max_height=1920)
    artwork_filename = fields.Char(string='Artwork Filename')
    
    @api.constrains('media_face_id', 'media_digital_screen_id', 'start_date', 'end_date', 'state')
    def _check_availability(self):
        for line in self:
            if not line.start_date or not line.end_date:
                continue
            
            # Check for overlapping bookings for static faces
            if line.media_face_id and line.media_face_id.face_type != 'digital':
                domain = [
                    ('id', '!=', line.id),
                    ('media_face_id', '=', line.media_face_id.id),
                    ('state', 'in', ['sale', 'done']),
                    ('start_date', '<=', line.end_date),
                    ('end_date', '>=', line.start_date),
                ]
                overlapping = self.search_count(domain)
                if overlapping:
                    raise ValidationError(_('The face %s is already booked for the selected period.') % line.media_face_id.name)

            # Check for overlapping bookings for digital screens is handled by the slot logic or SOV rules.
            # But the constraint signature must include media_digital_screen_id if we want logic for it in future.

    @api.onchange('media_face_id')
    def _onchange_media_face_id(self):
        if self.media_face_id:
            if not self.product_id:
                generic_product = self.env['product.product'].search([('name', '=', 'Advertising Service')], limit=1)
                if generic_product:
                    self.product_id = generic_product
                elif self.media_face_id.product_id:
                    self.product_id = self.media_face_id.product_id
            
            # Set price based on pricing type
            if self.media_face_id.pricing_type == 'fixed':
                self.price_unit = self.media_face_id.price_per_month
            elif self.media_face_id.pricing_type == 'daily':
                self.price_unit = self.media_face_id.price_per_day
            

            self._onchange_lease_duration()

    @api.onchange('canopy_id')
    def _onchange_canopy_id(self):
        if self.canopy_id:
            if not self.product_id:
                generic_product = self.env['product.product'].search([('name', '=', 'Advertising Service')], limit=1)
                if generic_product:
                    self.product_id = generic_product
            # We don't have explicit product_id mapped to canopy in site.py right now,
            self._onchange_lease_duration()

    @api.onchange('media_digital_screen_id')
    def _onchange_media_digital_screen_id(self):
        if self.media_digital_screen_id:
            screen = self.media_digital_screen_id
            if not self.product_id:
                generic_product = self.env['product.product'].search([('name', '=', 'Advertising Service')], limit=1)
                if generic_product:
                    self.product_id = generic_product
                elif screen.product_id:
                    self.product_id = screen.product_id
            
            # Set price based on pricing type
            # For digital screens, we usually sell per slot or fixed
            if screen.pricing_type == 'fixed':
                self.price_unit = screen.price_per_month
            elif screen.pricing_type == 'slot_monthly':
                self.price_unit = screen.price_slot_monthly
            

            self._onchange_lease_duration()

    @api.onchange('product_id', 'media_face_id', 'media_digital_screen_id', 'canopy_id', 'start_date', 'end_date', 'media_slot_id')
    def _onchange_generate_custom_description(self):
        for line in self:
            desc_lines = []
            # if line.product_id:
            #     desc_lines.append(line.product_id.display_name)
            
            if line.start_date and line.end_date:
                desc_lines.append(f"Period: {line.start_date.strftime('%m/%d/%Y')} - {line.end_date.strftime('%m/%d/%Y')}")
            
            if line.media_face_id:
                face = line.media_face_id
                face_code = getattr(face, 'code', False) or face.name
                size_str = f"Size: {face.width}x{face.height} meters {face.orientation.capitalize() if face.orientation else ''}"
                loc_str = ""
                if face.site_id:
                    loc_parts = []
                    if face.site_id.street:
                        loc_parts.append(face.site_id.street)
                    elif face.site_id.site_category == 'billboard':
                        billboard = self.env['media.billboard'].search([('site_id', '=', face.site_id.id)], limit=1)
                        if billboard and billboard.location_text:
                            loc_parts.append(billboard.location_text)
                    
                    if face.site_id.sub_county_id:
                        loc_parts.append(face.site_id.sub_county_id.name)
                    if face.site_id.county_id:
                        loc_parts.append(face.site_id.county_id.name)
                    loc_str = f" | Loc: {', '.join(loc_parts)}" if loc_parts else ""
                
                desc_lines.append(f"{face_code} {size_str}{loc_str}".strip())
                
            elif line.media_digital_screen_id:
                screen = line.media_digital_screen_id
                screen_code = getattr(screen, 'code', False) or screen.name
                size_str = f"Size: {screen.width}x{screen.height} meters"
                loc_str = ""
                if screen.site_id:
                    loc_parts = []
                    if screen.site_id.street:
                        loc_parts.append(screen.site_id.street)
                    if screen.site_id.sub_county_id:
                        loc_parts.append(screen.site_id.sub_county_id.name)
                    if screen.site_id.county_id:
                        loc_parts.append(screen.site_id.county_id.name)
                    loc_str = f" | Loc: {', '.join(loc_parts)}" if loc_parts else ""
                desc_lines.append(f"{screen_code} {size_str}{loc_str}".strip())
                
            elif hasattr(line, 'media_slot_id') and line.media_slot_id:
                slot = line.media_slot_id
                slot_code = getattr(slot, 'code', False) or slot.name
                size_str = ""
                if slot.digital_screen_id:
                    size_str = f" Size: {slot.digital_screen_id.width}x{slot.digital_screen_id.height} meters | "
                loc_str = ""
                if slot.digital_screen_id and slot.digital_screen_id.site_id:
                    loc_parts = []
                    if slot.digital_screen_id.site_id.street:
                         loc_parts.append(slot.digital_screen_id.site_id.street)
                    if slot.digital_screen_id.site_id.sub_county_id:
                         loc_parts.append(slot.digital_screen_id.site_id.sub_county_id.name)
                    if slot.digital_screen_id.site_id.county_id:
                         loc_parts.append(slot.digital_screen_id.site_id.county_id.name)
                    loc_str = f"Loc: {', '.join(loc_parts)}" if loc_parts else ""
                desc_lines.append(f"{slot_code}{size_str}{loc_str}".strip())

                # Add DOOH specific technical details
                if slot.digital_screen_id:
                    s = slot.digital_screen_id
                    if s.content_size_rec:
                        desc_lines.append(f"Content size: ({s.content_size_rec})")
                    if s.supported_formats:
                        desc_lines.append(f"Content type: {s.supported_formats}")
                    if s._fields.get('operating_hours_start') and s._fields.get('operating_hours_end'):
                        sh = int(s.operating_hours_start)
                        sm = int((s.operating_hours_start % 1) * 60)
                        eh = int(s.operating_hours_end)
                        em = int((s.operating_hours_end % 1) * 60)
                        desc_lines.append(f"Operating hours: {sh:02d}:{sm:02d} to {eh:02d}:{em:02d}")
                    if s._fields.get('slot_duration'):
                         dur = s.slot_duration
                         clients = s.number_of_slots
                         freq_min = int((dur * clients) / 60) if clients > 0 else 0
                         desc_lines.append(f"Content Duration: {dur}sec every {freq_min} min")
                    if s.views_per_day:
                         desc_lines.append(f"{s.views_per_day:,} views per day")
                    if s.number_of_slots:
                         desc_lines.append(f"Maximum clients: {s.number_of_slots}")

            elif line.canopy_id:
                canopy = line.canopy_id
                canopy_code = getattr(canopy, 'code', False) or canopy.name
                loc_str = ""
                if canopy.location_phone:
                    loc_str = f" | Loc: {canopy.location_phone}"
                elif canopy.site_id:
                    loc_parts = []
                    if canopy.site_id.street:
                         loc_parts.append(canopy.site_id.street)
                    if canopy.site_id.sub_county_id:
                         loc_parts.append(canopy.site_id.sub_county_id.name)
                    if canopy.site_id.county_id:
                         loc_parts.append(canopy.site_id.county_id.name)
                    loc_str = f" | Loc: {', '.join(loc_parts)}" if loc_parts else ""
                desc_lines.append(f"{canopy_code}{loc_str}".strip())
                
            if len(desc_lines) > 1 or (len(desc_lines) == 1 and not line.name):
                line.name = "\n".join(desc_lines)


    @api.onchange('start_date', 'end_date')
    def _onchange_lease_duration(self):
        for line in self:
            if line.start_date and line.end_date:
                # Calculate duration in months
                delta = relativedelta(line.end_date, line.start_date)
                months = delta.years * 12 + delta.months
                if delta.days > 0:
                    # Approximation: 30 days = 1 month
                    months += round(delta.days / 30.0, 2)
                
                # We expect billboards/canopies/slots to be sold per month
                if line.media_face_id or line.media_digital_screen_id or line.canopy_id or (hasattr(line, 'media_slot_id') and line.media_slot_id):
                     line.product_uom_qty = max(months, 0)

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        res.update({
            'start_date': self.start_date,
            'end_date': self.end_date,
            'artwork_file': self.artwork_file,
            'artwork_filename': self.artwork_filename,
        })
        if self.media_face_id:
            res['media_face_id'] = self.media_face_id.id
        if self.media_digital_screen_id:
            res['media_digital_screen_id'] = self.media_digital_screen_id.id
        if self.canopy_id:
            res['canopy_id'] = self.canopy_id.id
        return res
    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)
        if 'artwork_file' in vals and vals['artwork_file']:
            for line in self:
                history_vals = {
                    'sale_order_line_id': line.id,
                    'artwork_file': vals['artwork_file'],
                    'description': _('Updated artwork for contract %s') % line.order_id.name,
                }
                if line.media_face_id:
                    history_vals['face_id'] = line.media_face_id.id
                elif line.canopy_id:
                    history_vals.update({
                        'site_id': line.canopy_id.site_id.id,
                        'site_category': 'canopy',
                    })
                elif line.media_digital_screen_id:
                    history_vals.update({
                        'site_id': line.media_digital_screen_id.site_id.id,
                        'site_category': 'digital',
                    })
                
                if history_vals.get('face_id') or history_vals.get('site_id'):
                    self.env['media.artwork.history'].create(history_vals)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        for line in lines:
            if line.artwork_file:
                history_vals = {
                    'sale_order_line_id': line.id,
                    'artwork_file': line.artwork_file,
                    'description': _('Initial artwork for contract %s') % line.order_id.name,
                }
                if line.media_face_id:
                    history_vals['face_id'] = line.media_face_id.id
                elif line.canopy_id:
                    history_vals.update({
                        'site_id': line.canopy_id.site_id.id,
                        'site_category': 'canopy',
                    })
                elif line.media_digital_screen_id:
                    history_vals.update({
                        'site_id': line.media_digital_screen_id.site_id.id,
                        'site_category': 'digital',
                    })
                
                if history_vals.get('face_id') or history_vals.get('site_id'):
                    self.env['media.artwork.history'].create(history_vals)
        return lines
