from odoo import models, fields, api, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    media_face_id = fields.Many2one('media.face', string='Media Face')
    media_digital_screen_id = fields.Many2one('media.digital.screen', string='Digital Screen')
    canopy_id = fields.Many2one('media.canopy', string='Canopy')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    item_description = fields.Text(string='Item Description')
    artwork_file = fields.Image(string='Artwork/Graphic', max_width=1920, max_height=1920)
    artwork_filename = fields.Char(string='Artwork Filename')
    move_payment_state = fields.Selection(related='move_id.payment_state', string='Payment Status')

    @api.onchange('product_id', 'media_face_id', 'media_digital_screen_id', 'canopy_id', 'start_date', 'end_date')
    def _onchange_generate_custom_description(self):
        for line in self:
            desc_lines = []
            
            # 1. Site / Face / Canopy / Slot details first
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

            # 2. Period comes second
            if line.start_date and line.end_date:
                desc_lines.append(f"Period: {line.start_date.strftime('%m/%d/%Y')} - {line.end_date.strftime('%m/%d/%Y')}")

            # 3. Technical details for DOOH (stays at bottom if applicable)
            if (line.media_digital_screen_id):
                s = line.media_digital_screen_id
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
                
            if len(desc_lines) > 0:
                line.item_description = "\n".join(desc_lines)
            else:
                line.item_description = False

class MediaFace(models.Model):
    _inherit = 'media.face'

    invoice_line_ids = fields.One2many('account.move.line', 'media_face_id', string='Invoice Lines')
