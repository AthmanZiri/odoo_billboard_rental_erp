from odoo import models, fields, api, _

class MediaResequenceWizard(models.TransientModel):
    _name = 'media.resequence.wizard'
    _description = 'Resequence Media Assets'

    prefix_type = fields.Selection([
        ('site', 'SITE/'),
        ('canopy', 'CAN/'),
        ('custom', 'Custom Prefix')
    ], string='Prefix Type', default='site', required=True)

    custom_prefix = fields.Char(string='Custom Prefix')
    start_number = fields.Integer(string='Start Number', default=1, required=True)
    padding = fields.Integer(string='Padding', default=4, required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(MediaResequenceWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            # Check if all selected records are canopies to set default prefix
            records = self.env[self.env.context.get('active_model')].browse(active_ids)
            # Try to guess prefix based on active_model or records
            if self.env.context.get('active_model') == 'media.canopy':
                res['prefix_type'] = 'canopy'
        return res

    def action_resequence(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return

        active_model = self.env.context.get('active_model')
        records = self.env[active_model].browse(active_ids)
        
        # Sort records by sequence field (if exists) or by current name
        # We want to maintain the drag-and-drop order
        sorted_records = records.sorted(key=lambda r: (r.sequence, r.name, r.id))

        prefix = self.custom_prefix if self.prefix_type == 'custom' else (
            'SITE/' if self.prefix_type == 'site' else 'CAN/'
        )

        current_number = self.start_number
        for record in sorted_records:
            new_name = f"{prefix}{str(current_number).zfill(self.padding)}"
            # Update the name. For inherited models, this updates the underlying media.site record.
            record.write({'name': new_name})
            current_number += 1
            
        return {'type': 'ir.actions.client', 'tag': 'reload'}
