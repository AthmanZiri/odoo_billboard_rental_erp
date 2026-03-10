# update_paperformat_margins.py
# Run this script using odoo shell to update paper format margins
# Usage: odoo shell -d <db_name> < update_paperformat_margins.py

PaperFormat = env['report.paperformat']
formats = PaperFormat.search([])

for pf in formats:
    if pf.margin_top < 65:
        print(f"Updating {pf.name}: margin_top {pf.margin_top} -> 65, header_spacing {pf.header_spacing} -> 60")
        pf.margin_top = 65
        pf.header_spacing = 60

env.cr.commit()
print("SUCCESS - Margins Updated!")
