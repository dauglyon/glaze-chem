"""
N-axial blend generation for ceramic glazes.

Generates blend points across N recipe corners using simplex lattice.
Supports line blends (2), triaxial (3), quadraxial (4), and beyond.
"""

from itertools import combinations_with_replacement


def simplex_lattice(n_corners, steps):
    """
    Generate all blend points for N corners with given steps.

    Args:
        n_corners: number of recipe corners (2=line, 3=triaxial, etc.)
        steps: number of divisions along each edge

    Returns:
        list of tuples, each tuple contains fractions summing to 1.0
        For steps=5: fractions are 0, 0.25, 0.5, 0.75, 1.0

    Example:
        simplex_lattice(2, 3) -> [(1.0, 0.0), (0.5, 0.5), (0.0, 1.0)]
        simplex_lattice(3, 3) -> [(1,0,0), (0.5,0.5,0), (0.5,0,0.5), ...]
    """
    if steps < 2:
        steps = 2

    divisions = steps - 1
    points = []

    # Generate all combinations of n_corners non-negative integers that sum to divisions
    def partitions(total, parts, current=[]):
        if parts == 1:
            yield current + [total]
            return
        for i in range(total + 1):
            yield from partitions(total - i, parts - 1, current + [i])

    for partition in partitions(divisions, n_corners):
        # Reverse so first corner starts at 100%
        fractions = tuple(p / divisions for p in reversed(partition))
        points.append(fractions)

    return points


def blend_point_name(fractions, steps):
    """
    Generate grid coordinate name for a blend point.

    Args:
        fractions: tuple of fractions for each corner
        steps: number of steps (for converting fractions to indices)

    Returns:
        string like "1" (line), "1-3" (triaxial), "1-2-3" (quadraxial)
        For line blends: 1 = 100% first corner, N = 100% second corner
    """
    divisions = steps - 1

    if len(fractions) == 2:
        # Line blend: position from first to second corner
        # 100% first = 1, 100% second = steps
        position = int(round((1 - fractions[0]) * divisions)) + 1
        return str(position)
    else:
        # Multi-axial: grid coordinates based on each corner's fraction
        indices = [int(round(f * divisions)) + 1 for f in fractions]
        return "-".join(str(i) for i in indices)


def blend_recipes(corner_recipes, fractions):
    """
    Create a blended recipe from corner recipes.

    Args:
        corner_recipes: list of recipe dicts (material_id -> parts)
        fractions: tuple of fractions for each corner (sum to 1.0)

    Returns:
        dict of material_id -> parts (normalized to 100)
    """
    blended = {}

    for recipe, fraction in zip(corner_recipes, fractions):
        # Normalize corner recipe to 100 first
        total = sum(recipe.values())
        if total == 0:
            continue

        for mat_id, parts in recipe.items():
            normalized = (parts / total) * 100
            contribution = normalized * fraction
            if contribution > 0:
                blended[mat_id] = blended.get(mat_id, 0) + contribution

    return blended


def generate_blends(corner_recipes, corner_names, steps, materials, flux_oxides=None):
    """
    Generate all blend points with recipes and UMF.

    Args:
        corner_recipes: list of recipe dicts (material_id -> parts)
        corner_names: list of recipe IDs/names
        steps: number of steps along each edge
        materials: materials dict for UMF calculation
        flux_oxides: optional flux oxide list for UMF

    Returns:
        list of dicts with:
            'name': grid coordinate name
            'fractions': tuple of corner fractions
            'recipe': blended recipe dict
            'umf': computed UMF
    """
    from solver import recipe_to_umf

    n_corners = len(corner_recipes)
    points = simplex_lattice(n_corners, steps)

    results = []
    for fractions in points:
        name = blend_point_name(fractions, steps)
        recipe = blend_recipes(corner_recipes, fractions)
        umf = recipe_to_umf(recipe, materials, flux_oxides)

        results.append({
            'name': name,
            'fractions': fractions,
            'corner_names': corner_names,
            'recipe': recipe,
            'umf': umf
        })

    return results


def format_blend(blend, materials):
    """
    Format a single blend point as a string.

    Args:
        blend: dict from generate_blends()
        materials: materials dict for display names

    Returns:
        formatted string
    """
    from utils import format_umf_table

    lines = []

    # Header with corner contributions
    corner_parts = []
    for name, frac in zip(blend['corner_names'], blend['fractions']):
        if frac > 0:
            corner_parts.append(f"{name}:{frac*100:.0f}%")
    lines.append(f"Blend {blend['name']} ({', '.join(corner_parts)})")
    lines.append("-" * 40)

    # Recipe
    lines.append("Recipe:")
    for mat_id, parts in sorted(blend['recipe'].items(), key=lambda x: -x[1]):
        if parts >= 0.1:
            name = materials.get(mat_id, {}).get('name', mat_id)
            lines.append(f"  {name:20} {parts:6.1f}")

    # UMF
    lines.append("")
    lines.append("UMF:")
    lines.append(format_umf_table(blend['umf']))

    return '\n'.join(lines)


def format_blends(blends, materials):
    """
    Format all blend points as a string.

    Args:
        blends: list from generate_blends()
        materials: materials dict

    Returns:
        formatted string with all blends
    """
    # Sort by name for consistent ordering
    sorted_blends = sorted(blends, key=lambda b: b['name'])

    sections = []
    for blend in sorted_blends:
        sections.append(format_blend(blend, materials))

    return '\n\n'.join(sections)
