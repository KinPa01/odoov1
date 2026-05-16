import os
import re

directory = r"c:\Users\autod\Desktop\inten\warehousepart\odoo\addons\warehousepart\data"
for filename in os.listdir(directory):
    if filename.endswith('.xml'):
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # In Odoo, cross-module references use module_name.xml_id.
        # Here, the code incorrectly used file_name.xml_id like "spare_category_data.cat_oil"
        # We replace any ref="spare_xxxx.yyy" with ref="yyy" (since they are in the same module)
        new_content = re.sub(r'ref="spare_[^.]*\.([^"]+)"', r'ref="\1"', content)
        
        if content != new_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Updated {filename}')
print('Done!')
