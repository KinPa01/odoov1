kerry_carriers = env['delivery.carrier'].search([('name', 'ilike', 'Kerry')])
for k in kerry_carriers:
    k.write({'website_published': True, 'active': True})
    print(f"✅ Published Kerry Express (ID: {k.id})")
env.cr.commit()
