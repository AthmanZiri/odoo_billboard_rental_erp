import os

odoo_path = '/usr/lib/python3/dist-packages/odoo'
sol_path = os.path.join(odoo_path, 'addons/sale/models/sale_order_line.py')

if os.path.exists(sol_path):
    with open(sol_path, 'r') as f:
        content = f.read()
        print("Found sale_order_line.py")
        if 'product_uom' in content:
            print("product_uom found in sale_order_line.py")
        else:
            print("product_uom NOT found in sale_order_line.py")
            # Let's search for what it might be
            import re
            uom_fields = re.findall(r'(\w*uom\w*)', content)
            print("UoM related fields found:", set(uom_fields))
else:
    print(f"Could not find {sol_path}")
