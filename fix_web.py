for code, cat_ref in [
    ('OIL-10W40-001', 'warehousepart.web_category_oil'),
    ('BRK-VIOS-001', 'warehousepart.web_category_brk'),
    ('FIL-HONDA-001', 'warehousepart.web_category_fil'),
    ('BAT-NS60-001', 'warehousepart.web_category_bat'),
    ('SUS-VIGO-001', 'warehousepart.web_category_sus')
]:
    product = env['product.template'].search([('default_code', '=', code)], limit=1)
    if product:
        cat = env.ref(cat_ref, raise_if_not_found=False)
        if cat:
            product.write({
                'is_published': True,
                'public_categ_ids': [(6, 0, [cat.id])]
            })
            print('Fixed', code, 'with category', cat.name)
env.cr.commit()
