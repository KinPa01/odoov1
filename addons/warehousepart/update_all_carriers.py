carriers = env['delivery.carrier'].search([])
print("--- Updating Carriers in ran_ahlai_prod ---")
for c in carriers:
    if c.id == 1:
        c.write({'website_published': True, 'active': True, 'country_ids': [(5,0,0)]})
        print(f"✅ Published: {c.name}")
    elif c.id == 9:
        c.write({'website_published': True, 'active': True})
        print(f"✅ Published: {c.name}")

env.cr.commit()

print("\n📋 Delivery Carriers in ran_ahlai_prod:")
for c in env['delivery.carrier'].search([]):
    print(f"  [{c.id}] {c.name:30} | {getattr(c,'fixed_price',0):5.0f}฿ | pub={c.website_published} | country={c.country_ids.mapped('name')}")
