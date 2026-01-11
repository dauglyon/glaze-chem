"""
YAML-based format for storing glaze data: materials, recipes, and UMF.

Standalone UMF:
    name: My Glaze
    flux:
      K2O: 0.26
      CaO: 0.74
    other:
      SiO2: 3.70
      Al2O3: 0.35

Materials:
    materials:
      custer_feldspar:
        name: Custer Feldspar
        loi: 0.15
        analysis:
          SiO2: 68.5
          Al2O3: 18.2
          K2O: 10.0

Recipes (with optional UMF):
    recipes:
      cone10_clear:
        name: Cone 10 Clear
        materials:
          custer_feldspar: 40
          silica: 30
          whiting: 20
        umf:
          flux:
            K2O: 0.26
            CaO: 0.74
          other:
            SiO2: 3.70
"""

import yaml
from pathlib import Path


def _normalize_oxide(name):
    """Normalize oxide names to standard capitalization."""
    patterns = {
        'sio2': 'SiO2', 'al2o3': 'Al2O3', 'b2o3': 'B2O3',
        'na2o': 'Na2O', 'k2o': 'K2O', 'li2o': 'Li2O',
        'cao': 'CaO', 'mgo': 'MgO', 'bao': 'BaO', 'sro': 'SrO',
        'zno': 'ZnO', 'pbo': 'PbO', 'mno': 'MnO',
        'fe2o3': 'Fe2O3', 'feo': 'FeO',
        'tio2': 'TiO2', 'zro2': 'ZrO2', 'sno2': 'SnO2',
        'cuo': 'CuO', 'cu2o': 'Cu2O',
        'coo': 'CoO', 'nio': 'NiO',
        'cr2o3': 'Cr2O3', 'mno2': 'MnO2',
        'p2o5': 'P2O5', 'v2o5': 'V2O5',
        'bi2o3': 'Bi2O3',
        'ceo2': 'CeO2', 'la2o3': 'La2O3', 'nd2o3': 'Nd2O3',
        'pr2o3': 'Pr2O3', 'er2o3': 'Er2O3', 'y2o3': 'Y2O3',
        'f': 'F',
    }
    return patterns.get(name.lower(), name)


def _normalize_oxides(d):
    """Normalize all oxide keys in a dict."""
    return {_normalize_oxide(k): v for k, v in d.items()}


def _load_yaml(source):
    """Load YAML from file path or string."""
    if isinstance(source, (str, Path)) and not '\n' in str(source):
        with open(source) as f:
            return yaml.safe_load(f)
    else:
        return yaml.safe_load(source)


# --- UMF ---

def read_umf(source):
    """
    Read UMF from YAML. Supports standalone UMF or extracted from recipe.

    Returns dict with 'name' (optional), 'flux', 'other' oxide dicts.
    """
    data = _load_yaml(source)

    result = {
        'name': data.get('name'),
        'flux': {},
        'other': {}
    }

    if 'flux' in data:
        result['flux'] = _normalize_oxides(data['flux'])
    if 'other' in data:
        result['other'] = _normalize_oxides(data['other'])

    return result


def write_umf(umf, path=None):
    """
    Write UMF to YAML format.

    Args:
        umf: dict with 'name' (optional), 'flux', 'other' keys
             OR dict with flux_oxides list for auto-grouping
        path: file path (optional, returns string if None)
    """
    output = {}

    if umf.get('name'):
        output['name'] = umf['name']

    if 'flux' in umf:
        output['flux'] = dict(umf['flux'])
    if 'other' in umf:
        output['other'] = dict(umf['other'])

    result = yaml.dump(output, default_flow_style=False, sort_keys=False)

    if path:
        with open(path, 'w') as f:
            f.write(result)
    else:
        return result


def format_umf_table(umf_data, flux_oxides=None):
    """
    Format UMF data as a readable string table.

    Args:
        umf_data: dict of oxide: value, or structured UMF from read_umf
        flux_oxides: list of oxide names to group as fluxes (optional)
    """
    # Handle structured UMF (from read_umf)
    if 'flux' in umf_data and 'other' in umf_data:
        lines = []
        if umf_data.get('name'):
            lines.append(f"UMF: {umf_data['name']}")
            lines.append("-" * 30)

        flux_sum = sum(umf_data['flux'].values())
        lines.append("Flux:")
        for ox, val in umf_data['flux'].items():
            lines.append(f"  {ox:8} {val:.3f}")
        lines.append(f"  {'TOTAL':8} {flux_sum:.3f}")
        lines.append("")
        lines.append("Other:")
        for ox, val in umf_data['other'].items():
            lines.append(f"  {ox:8} {val:.3f}")
        return '\n'.join(lines)

    # Handle flat dict with flux_oxides list
    oxides = umf_data
    lines = []

    if flux_oxides:
        flux_sum = 0
        lines.append("Flux:")
        for ox in flux_oxides:
            if ox in oxides:
                lines.append(f"  {ox:8} {oxides[ox]:.3f}")
                flux_sum += oxides[ox]
        lines.append(f"  {'TOTAL':8} {flux_sum:.3f}")
        lines.append("")
        lines.append("Other:")
        for ox, val in oxides.items():
            if ox not in flux_oxides:
                lines.append(f"  {ox:8} {val:.3f}")
    else:
        for ox, val in oxides.items():
            lines.append(f"{ox:8} {val:.3f}")

    return '\n'.join(lines)


# --- Materials ---

def read_materials(source):
    """
    Read materials from YAML.

    Returns dict mapping material_id -> {name, loi, analysis}
    """
    data = _load_yaml(source)

    materials_data = data.get('materials', data)
    result = {}

    for mat_id, mat in materials_data.items():
        result[mat_id] = {
            'name': mat.get('name', mat_id),
            'loi': mat.get('loi', 0),
            'analysis': _normalize_oxides(mat.get('analysis', {}))
        }

    return result


def write_materials(materials, path=None):
    """
    Write materials to YAML format.
    """
    output = {'materials': {}}

    for mat_id, mat in materials.items():
        entry = {}
        if mat.get('name') and mat['name'] != mat_id:
            entry['name'] = mat['name']
        if mat.get('loi'):
            entry['loi'] = mat['loi']
        entry['analysis'] = dict(mat['analysis'])
        output['materials'][mat_id] = entry

    result = yaml.dump(output, default_flow_style=False, sort_keys=False)

    if path:
        with open(path, 'w') as f:
            f.write(result)
    else:
        return result


# --- Recipes ---

def read_recipes(source):
    """
    Read recipes from YAML.

    Returns dict mapping recipe_id -> {name, materials, umf (optional)}
    """
    data = _load_yaml(source)

    recipes_data = data.get('recipes', {})
    result = {}

    for recipe_id, recipe in recipes_data.items():
        entry = {
            'name': recipe.get('name', recipe_id),
            'materials': dict(recipe.get('materials', {}))
        }
        if 'umf' in recipe:
            entry['umf'] = {
                'flux': _normalize_oxides(recipe['umf'].get('flux', {})),
                'other': _normalize_oxides(recipe['umf'].get('other', {}))
            }
        result[recipe_id] = entry

    return result


def write_recipes(recipes, path=None):
    """
    Write recipes to YAML format.
    """
    output = {'recipes': {}}

    for recipe_id, recipe in recipes.items():
        entry = {}
        if recipe.get('name') and recipe['name'] != recipe_id:
            entry['name'] = recipe['name']
        entry['materials'] = dict(recipe['materials'])
        if recipe.get('umf'):
            entry['umf'] = {
                'flux': dict(recipe['umf']['flux']),
                'other': dict(recipe['umf']['other'])
            }
        output['recipes'][recipe_id] = entry

    result = yaml.dump(output, default_flow_style=False, sort_keys=False)

    if path:
        with open(path, 'w') as f:
            f.write(result)
    else:
        return result


# --- Combined file ---

def read_glaze_file(source):
    """
    Read a combined glaze file with materials and recipes.

    Returns dict with 'materials' and 'recipes' keys.
    """
    data = _load_yaml(source)

    result = {
        'materials': {},
        'recipes': {}
    }

    if 'materials' in data:
        result['materials'] = read_materials(data)

    if 'recipes' in data:
        result['recipes'] = read_recipes(data)

    return result


def write_glaze_file(data, path=None):
    """
    Write a combined glaze file.
    """
    output = {}

    if data.get('materials'):
        mats = write_materials(data['materials'])
        output.update(yaml.safe_load(mats))

    if data.get('recipes'):
        recs = write_recipes(data['recipes'])
        output.update(yaml.safe_load(recs))

    result = yaml.dump(output, default_flow_style=False, sort_keys=False)

    if path:
        with open(path, 'w') as f:
            f.write(result)
    else:
        return result
