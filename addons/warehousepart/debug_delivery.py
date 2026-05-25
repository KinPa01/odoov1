# Debug อย่างละเอียด: simulate _is_available_for_order
carriers = env['delivery.carrier'].search([('website_published','=',True)])

# หา order ล่าสุดที่ state='draft' (cart) หรือ SO ล่าสุด
order = env['sale.order'].search([('state','in',['draft','sale'])], limit=1, order='id desc')
if not order:
    print("ไม่พบ order")
else:
    print(f"Test order: {order.name} | partner_shipping: {order.partner_shipping_id.name}")
    print(f"partner country: {order.partner_shipping_id.country_id.name or 'NONE'}")
    print(f"partner state: {order.partner_shipping_id.state_id.name or 'NONE'}")
    print(f"partner zip: {order.partner_shipping_id.zip or 'NONE'}")
    print()
    for c in carriers:
        print(f"--- {c.name} ---")
        print(f"  country_ids: {c.country_ids.mapped('name')}")
        print(f"  state_ids: {c.state_ids.mapped('name') if hasattr(c,'state_ids') else 'N/A'}")
        print(f"  zip_prefix_ids: {c.zip_prefix_ids.mapped('name') if hasattr(c,'zip_prefix_ids') else 'N/A'}")
        print(f"  must_have_tag_ids: {c.must_have_tag_ids.mapped('name') if hasattr(c,'must_have_tag_ids') else 'N/A'}")
        print(f"  excluded_tag_ids: {c.excluded_tag_ids.mapped('name') if hasattr(c,'excluded_tag_ids') else 'N/A'}")
        print(f"  max_weight: {getattr(c,'max_weight',0)}")
        
        match_addr = c._match_address(order.partner_shipping_id)
        print(f"  _match_address: {match_addr}")
        try:
            match_must = c._match_must_have_tags(order)
            print(f"  _match_must_have_tags: {match_must}")
        except Exception as e:
            print(f"  _match_must_have_tags ERROR: {e}")
        try:
            match_excl = c._match_excluded_tags(order)
            print(f"  _match_excluded_tags: {match_excl}")
        except Exception as e:
            print(f"  _match_excluded_tags ERROR: {e}")
        try:
            match_weight = c._match_weight(order)
            print(f"  _match_weight: {match_weight}")
        except Exception as e:
            print(f"  _match_weight ERROR: {e}")
        try:
            avail = c._is_available_for_order(order)
            print(f"  ✅ _is_available_for_order: {avail}")
        except Exception as e:
            print(f"  ❌ _is_available_for_order ERROR: {e}")
        print()
