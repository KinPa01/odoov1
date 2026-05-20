import sys

HOMEPAGE_KEY = 'warehousepart.ran_ahlai_homepage'

print("=" * 60)
print("Searching for old website-builder-generated views...")
print("=" * 60)

parent_views = env['ir.ui.view'].search([('key', '=', HOMEPAGE_KEY)])

if not parent_views:
    print(f"ERROR: Parent view '{HOMEPAGE_KEY}' not found!")
    sys.exit(0)

for parent_view in parent_views:
    print(f"Found parent view: ID={parent_view.id}, name={parent_view.name}")

    child_views = env['ir.ui.view'].search([
        ('inherit_id', '=', parent_view.id),
    ])

    print(f"  Found {len(child_views)} child views.")

    # Delete builder-generated child views
    builder_views = child_views.filtered(
        lambda v: not v.key or v.key.startswith('website.')
    )
    print(f"  Deleting {len(builder_views)} website-builder-generated child views...")
    for bv in builder_views:
        print(f"    Deleting: ID={bv.id}, name={bv.name}, key={bv.key}")
    builder_views.unlink()

    # Reset parent view arch
    print("  Resetting parent view arch to XML template...")
    parent_view.write({'arch_updated': False})

env.cr.commit()
print("\nDone! Please restart Odoo and refresh the page.")
print("=" * 60)
sys.exit(0)
