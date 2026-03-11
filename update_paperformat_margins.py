# update_paperformat_margins.py
# Run this script using odoo shell to update paper format margins
# Usage: odoo shell -d <db_name> < update_paperformat_margins.py

# IMPORTANT: You MUST pass the database name using -d <db_name>
# Otherwise 'env' will not be initialized.

import sys

if 'env' not in locals():
    print("ERROR: 'env' is not defined. Did you remember to specify the database with '-d <db_name>'?")
    print("Example: odoo shell -d lookon_ltd < update_paperformat_margins.py")
    sys.exit(1)

PaperFormat = env['report.paperformat']
formats = PaperFormat.search([])

for pf in formats:
    if pf.margin_top > 20:
        print(f"Updating {pf.name}: margin_top {pf.margin_top} -> 55, header_spacing {pf.header_spacing} -> 65")
        pf.margin_top = 55
        pf.header_spacing = 65
    
    if pf.margin_bottom > 55:
        print(f"Updating {pf.name}: margin_bottom {pf.margin_bottom} -> 55")
        pf.margin_bottom = 55

env.cr.commit()
print("SUCCESS - Margins Updated!")
