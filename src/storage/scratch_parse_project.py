import xml.etree.ElementTree as ET

file_path = r'c:\pythonproject\tech_modul\Export z 3DConstructor\test importu.project'
tree = ET.parse(file_path)
root = tree.getroot()

objs = root.findall(".//ProjectStructure/Obj")
for i, o in enumerate(objs):
    if o.get('class') == '1': # Assembly
        print(f"Module: {o.get('name')}")
        for prop in o.findall('property'):
            print(f"  Property: {prop.get('name')} = {prop.get('value')}")
        # Also check ANY child
        for child in o:
            if child.tag != 'property':
                print(f"  Child: {child.tag} -> {child.attrib}")
        break
