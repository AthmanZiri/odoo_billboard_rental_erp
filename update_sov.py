import re
lines = env['sale.order.line'].search([('name', 'ilike', '| SOV:')])
count = 0
for line in lines:
    new_name = re.sub(r'\s*\|\s*SOV:\s*[\d\.]+%?', '', line.name)
    if new_name != line.name:
        line.write({'name': new_name})
        count += 1
env.cr.commit()
print(f"Updated {count} sale order lines.")
