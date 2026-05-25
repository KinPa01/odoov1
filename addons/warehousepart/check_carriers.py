carriers = env['delivery.carrier'].search([])
print(f'Delivery carriers: {len(carriers)}')
for c in carriers:
    pub = getattr(c, 'website_published', 'N/A')
    print(f'  [{c.id}] {c.name} | active={c.active} | published={pub} | country={c.country_ids.mapped("name")}')
