"""
Coefficient of Thermal Expansion (CTE) calculation for ceramic glazes.

CTE is calculated from oxide weight percentages using empirical coefficients.
Result is in units of x10⁻⁶/°C (ppm/°C).

Coefficients from West & Gerrow, "Ceramic Science for the Potter",
as used by Digitalfire and Glazy.

References:
- https://digitalfire.com/glossary/calculated+thermal+expansion
- https://help.glazy.org/concepts/analysis/cte.html
- https://johnsankey.ca/glazeexpansion.html
"""

# CTE coefficients (weight percent basis)
# Multiply oxide wt% by coefficient, sum for total CTE
CTE_COEFFICIENTS = {
    # Primary oxides - West & Gerrow
    "SiO2": 0.035,
    "Al2O3": 0.063,
    "Na2O": 0.390,
    "K2O": 0.331,
    "CaO": 0.148,
    "MgO": 0.030,
    "Fe2O3": 0.130,
    "TiO2": 0.140,
    "ZrO2": 0.020,

    # Boron - negative coefficient (reduces expansion)
    "B2O3": -0.065,

    # Lithium - derived from Appen molar factors
    "Li2O": 0.320,

    # Estimated from Appen and other sources
    "ZnO": 0.070,
    "BaO": 0.100,
    "SrO": 0.120,
    "PbO": 0.130,
    "MnO": 0.100,
    "CoO": 0.050,
    "CuO": 0.030,
    "NiO": 0.050,
    "SnO2": 0.020,
    "Bi2O3": 0.100,
}


def recipe_to_oxide_pct(recipe, materials):
    """
    Calculate oxide weight percentages from a recipe.

    Args:
        recipe: dict of material_id -> parts
        materials: dict from read_materials()

    Returns:
        dict of oxide -> weight percent (normalized to 100%)
    """
    total_oxides = {}
    total_loi = 0

    for mat_id, parts in recipe.items():
        mat = materials[mat_id]
        loi = mat.get('loi', 0)
        total_loi += parts * loi / 100

        for oxide, pct in mat['analysis'].items():
            contribution = parts * pct / 100
            total_oxides[oxide] = total_oxides.get(oxide, 0) + contribution

    # Normalize to 100%
    fired_weight = sum(total_oxides.values())
    if fired_weight == 0:
        return {}

    return {ox: (val / fired_weight) * 100 for ox, val in total_oxides.items()}


def calculate_cte(recipe, materials):
    """
    Calculate coefficient of thermal expansion for a glaze recipe.

    Args:
        recipe: dict of material_id -> parts
        materials: dict from read_materials()

    Returns:
        dict with:
            'cte': total CTE value (x10⁻⁶/°C)
            'contributions': dict of oxide -> (weight_pct, coefficient, contribution)
    """
    oxide_pct = recipe_to_oxide_pct(recipe, materials)

    contributions = {}
    total_cte = 0

    for oxide, pct in oxide_pct.items():
        coef = CTE_COEFFICIENTS.get(oxide, 0)
        if coef != 0:
            contribution = pct * coef
            total_cte += contribution
            contributions[oxide] = (pct, coef, contribution)

    # Sort by contribution (highest first)
    contributions = dict(sorted(
        contributions.items(),
        key=lambda x: abs(x[1][2]),
        reverse=True
    ))

    return {
        'cte': total_cte,
        'contributions': contributions
    }


def format_cte(result, verbose=False):
    """
    Format CTE result as a string.

    Args:
        result: dict from calculate_cte()
        verbose: if True, show oxide breakdown

    Returns:
        formatted string
    """
    lines = [f"CTE: {result['cte']:.1f}"]

    if verbose and result['contributions']:
        lines.append("")
        lines.append("Contributions:")
        for oxide, (pct, coef, contrib) in result['contributions'].items():
            lines.append(f"  {oxide:8} {pct:5.1f}%  x {coef:+.3f}  = {contrib:+5.2f}")

    return '\n'.join(lines)
