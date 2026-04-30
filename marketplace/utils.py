from collections import OrderedDict
import json

ATTRIBUTE_VALUE_SEPARATORS = ('|', ',', '，', ';', '；', '\n')
COLOR_ATTRIBUTE_NAMES = {
    'color', 'colour', '颜色', '色', 'couleur', 'teinte',
}


def normalize_attribute_name(name):
    return (name or '').strip()



def split_attribute_values(raw_value):
    value = (raw_value or '').strip()
    if not value:
        return []

    values = [value]
    for separator in ATTRIBUTE_VALUE_SEPARATORS:
        if separator in value:
            values = [part.strip() for part in value.split(separator)]
            break

    unique_values = []
    seen = set()
    for item in values:
        if item and item not in seen:
            unique_values.append(item)
            seen.add(item)
    return unique_values



def build_attribute_groups(attributes):
    grouped = OrderedDict()

    for attribute in attributes:
        name = normalize_attribute_name(attribute.name)
        if not name:
            continue

        bucket = grouped.setdefault(name, [])
        for value in split_attribute_values(attribute.value):
            if value not in bucket:
                bucket.append(value)

    groups = []
    selectable_groups = []
    specification_groups = []

    for name, values in grouped.items():
        group = {
            'name': name,
            'values': values,
            'is_selectable': len(values) > 1,
            'is_color': name.strip().lower() in COLOR_ATTRIBUTE_NAMES,
            'display_value': ' / '.join(values),
        }
        groups.append(group)
        if group['is_selectable']:
            selectable_groups.append(group)
        else:
            specification_groups.append(group)

    return {
        'groups': groups,
        'selectable_groups': selectable_groups,
        'specification_groups': specification_groups,
    }



def normalize_selected_attributes(raw_value):
    if not raw_value:
        return {}

    if isinstance(raw_value, dict):
        data = raw_value
    else:
        try:
            data = json.loads(raw_value)
        except (TypeError, ValueError):
            return {}

    normalized = OrderedDict()
    for key, value in data.items():
        clean_key = normalize_attribute_name(key)
        clean_value = (value or '').strip()
        if clean_key and clean_value:
            normalized[clean_key] = clean_value
    return dict(normalized)



def validate_selected_attributes(attribute_groups, selected_attributes):
    normalized = normalize_selected_attributes(selected_attributes)
    errors = []
    cleaned = {}

    for group in attribute_groups.get('selectable_groups', []):
        selected_value = normalized.get(group['name'])
        if not selected_value:
            errors.append(f"请选择「{group['name']}」")
            continue
        if selected_value not in group['values']:
            errors.append(f"「{group['name']}」的选项无效")
            continue
        cleaned[group['name']] = selected_value

    return {
        'is_valid': not errors,
        'errors': errors,
        'cleaned': cleaned,
    }
