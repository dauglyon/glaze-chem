"""
Solve for UMF equivalence using candidate materials.

Given a target recipe (with its UMF) and a set of candidate materials,
find proportions of candidates that produce an equivalent UMF.
"""

import warnings
import numpy as np
from scipy.optimize import differential_evolution, NonlinearConstraint

warnings.filterwarnings('ignore', message='delta_grad == 0.0')

from utils import read_materials, read_recipes, read_umf, read_constraints, format_umf_table


# Oxide groupings
FLUX_TRADITIONAL = ["Li2O", "Na2O", "K2O", "CaO", "MgO", "SrO", "BaO", "ZnO"]
FLUX_EXTENDED = FLUX_TRADITIONAL + ["CoO", "CuO", "Fe2O3", "MnO2", "SnO2", "Bi2O3"]

# Default for backwards compatibility
FLUX_OXIDES = FLUX_TRADITIONAL

MOLECULAR_WEIGHT = {
    "SiO2": 60.085, "Al2O3": 101.961, "B2O3": 69.620, "TiO2": 79.866,
    "Li2O": 29.881, "Na2O": 61.979, "K2O": 94.196,
    "MgO": 40.304, "CaO": 56.077, "SrO": 103.619, "BaO": 153.326,
    "ZnO": 81.379, "Fe2O3": 159.688, "MnO": 70.937,
    "P2O5": 141.945, "ZrO2": 123.223,
    # Extended flux oxides
    "CoO": 74.932, "CuO": 79.545, "MnO2": 86.937,
    "SnO2": 150.71, "Bi2O3": 465.96,
}


def material_to_moles(material):
    """
    Calculate moles of each oxide per 100g of raw material.

    Args:
        material: single material dict with 'analysis' and optional 'loi'

    Returns:
        dict of oxide -> moles per 100g raw material
    """
    moles = {}
    for oxide, weight_pct in material['analysis'].items():
        if oxide in MOLECULAR_WEIGHT:
            moles[oxide] = weight_pct / MOLECULAR_WEIGHT[oxide]
    return moles


def recipe_to_umf(recipe, materials, flux_oxides=None):
    """
    Calculate UMF from a recipe and materials dict.

    Args:
        recipe: dict of material_id -> parts or {amount, add}
        materials: dict from read_materials()
        flux_oxides: list of oxide names to treat as fluxes (default: FLUX_TRADITIONAL)

    Returns:
        dict with 'flux' and 'other' oxide dicts
    """
    if flux_oxides is None:
        flux_oxides = FLUX_TRADITIONAL

    total_moles = {}

    for mat_id, mat_entry in recipe.items():
        # Handle both simple (number) and dict ({amount, add}) formats
        parts = mat_entry['amount'] if isinstance(mat_entry, dict) else mat_entry
        mat = materials[mat_id]
        mat_moles = material_to_moles(mat)
        for oxide, moles in mat_moles.items():
            total_moles[oxide] = total_moles.get(oxide, 0) + moles * parts / 100

    # Normalize to unity flux
    flux_total = sum(total_moles.get(ox, 0) for ox in flux_oxides)
    if flux_total == 0:
        flux_total = 1  # Avoid division by zero

    umf = {ox: mol / flux_total for ox, mol in total_moles.items()}

    # Split into flux and other
    flux = {ox: umf[ox] for ox in flux_oxides if ox in umf and umf[ox] > 0}
    other = {ox: val for ox, val in umf.items() if ox not in flux_oxides and val > 0}

    return {'flux': flux, 'other': other}


def select_candidates(target_umf, candidates):
    """
    Select materials from candidates that can contribute needed oxides.

    Args:
        target_umf: dict with 'flux' and 'other' oxide dicts
        candidates: dict from read_materials()

    Returns:
        list of material_ids that are useful for matching the target
    """
    target_oxides = set(target_umf['flux'].keys()) | set(target_umf['other'].keys())

    useful = []
    for mat_id, mat in candidates.items():
        mat_oxides = set(mat['analysis'].keys())
        # Include if it provides any oxide we need
        if mat_oxides & target_oxides:
            useful.append(mat_id)

    return useful


def solve_umf_match(target_umf, candidates, constraints=None, flux_oxides=None):
    """
    Find proportions of candidate materials that match target UMF.

    Uses global optimization (differential evolution) to find material
    proportions that produce a UMF matching the target, respecting
    min/max/fixed constraints.

    Args:
        target_umf: dict with 'flux' and 'other' oxide dicts
        candidates: dict from read_materials()
        constraints: optional dict of material_id -> {min, max} percentages
        flux_oxides: list of oxide names to treat as fluxes (default: FLUX_TRADITIONAL)

    Returns:
        dict with:
            'recipe': dict of material_id -> parts (normalized to 100)
            'umf': computed UMF of the solution
            'error': dict of oxide -> difference from target
            'selected': list of material_ids used
    """
    constraints = constraints or {}
    if flux_oxides is None:
        flux_oxides = FLUX_TRADITIONAL

    # Flatten target UMF to a single dict
    target_flat = {}
    target_flat.update(target_umf['flux'])
    target_flat.update(target_umf['other'])

    # Select useful candidates
    selected = select_candidates(target_umf, candidates)
    if not selected:
        return None

    # Separate fixed vs variable materials
    fixed_materials = {}
    variable_materials = []
    for mat_id in selected:
        c = constraints.get(mat_id, {})
        if c.get('min', 0) == c.get('max', 100) and 'min' in c:
            fixed_materials[mat_id] = c['min'] / 100
        else:
            variable_materials.append(mat_id)

    fixed_sum = sum(fixed_materials.values())
    if fixed_sum > 1:
        return None  # Fixed values exceed 100%

    if not variable_materials:
        # All materials are fixed - just compute the result
        recipe = {mat_id: val * 100 for mat_id, val in fixed_materials.items()}
        result_umf = recipe_to_umf(recipe, candidates, flux_oxides)
        result_flat = {}
        result_flat.update(result_umf['flux'])
        result_flat.update(result_umf['other'])
        error = {ox: result_flat.get(ox, 0) - target_flat.get(ox, 0) for ox in target_flat}
        return {'recipe': recipe, 'umf': result_umf, 'error': error, 'selected': list(recipe.keys())}

    # Build list of all oxides we care about
    all_oxides = sorted(target_flat.keys())
    flux_indices = [i for i, ox in enumerate(all_oxides) if ox in flux_oxides]

    # Build matrix M where M[i,j] = moles of oxide i per 1 part of material j
    n_oxides = len(all_oxides)

    # Precompute fixed contribution to moles
    fixed_moles = np.zeros(n_oxides)
    for mat_id, frac in fixed_materials.items():
        mat_moles = material_to_moles(candidates[mat_id])
        for i, oxide in enumerate(all_oxides):
            fixed_moles[i] += mat_moles.get(oxide, 0) * frac

    # Build matrix for variable materials only
    M = np.zeros((n_oxides, len(variable_materials)))
    for i, oxide in enumerate(all_oxides):
        for j, mat_id in enumerate(variable_materials):
            mat_moles = material_to_moles(candidates[mat_id])
            M[i, j] = mat_moles.get(oxide, 0)

    target_vec = np.array([target_flat[ox] for ox in all_oxides])

    # Build bounds for variable materials (as fractions, adjusted for fixed sum)
    remaining = 1 - fixed_sum
    bounds = []
    for mat_id in variable_materials:
        c = constraints.get(mat_id, {})
        lower = c.get('min', 0) / 100
        upper = min(c.get('max', 100) / 100, remaining)
        bounds.append((lower, upper))

    def objective(x):
        """Minimize squared UMF error."""
        total_moles = fixed_moles + M @ x
        flux_sum = sum(total_moles[i] for i in flux_indices)
        if flux_sum < 1e-10:
            return 1e10
        umf = total_moles / flux_sum
        return np.sum((umf - target_vec) ** 2)

    # Constraint: variable percentages sum to (1 - fixed_sum)
    sum_constraint = NonlinearConstraint(lambda x: np.sum(x), remaining, remaining)

    result = differential_evolution(
        objective,
        bounds=bounds,
        constraints=sum_constraint,
        seed=42,
        tol=1e-10,
        atol=1e-10,
        maxiter=2000,
        polish=True
    )

    if not result.success:
        return None

    # Build full recipe
    recipe = {}
    for mat_id, frac in fixed_materials.items():
        recipe[mat_id] = frac * 100

    threshold = 0.001
    for j, mat_id in enumerate(variable_materials):
        if result.x[j] > threshold:
            recipe[mat_id] = result.x[j] * 100

    if not recipe:
        return None

    # Calculate resulting UMF
    result_umf = recipe_to_umf(recipe, candidates, flux_oxides)

    # Calculate error
    result_flat = {}
    result_flat.update(result_umf['flux'])
    result_flat.update(result_umf['other'])

    error = {}
    for oxide in all_oxides:
        target_val = target_flat.get(oxide, 0)
        result_val = result_flat.get(oxide, 0)
        error[oxide] = result_val - target_val

    return {
        'recipe': recipe,
        'umf': result_umf,
        'error': error,
        'selected': list(recipe.keys())
    }


def format_solution(solution, materials):
    """
    Format a solution as a readable string.

    Args:
        solution: result from solve_umf_match()
        materials: dict from read_materials()

    Returns:
        formatted string showing recipe and UMF comparison
    """
    lines = []

    lines.append("Recipe:")
    lines.append("-" * 30)
    for mat_id, parts in sorted(solution['recipe'].items(), key=lambda x: -x[1]):
        name = materials[mat_id]['name']
        lines.append(f"  {name:20} {parts:6.1f}")
    lines.append(f"  {'TOTAL':20} {sum(solution['recipe'].values()):6.1f}")

    lines.append("")
    lines.append("Resulting UMF:")
    lines.append("-" * 30)
    lines.append(format_umf_table(solution['umf']))

    # Show error if significant
    max_error = max(abs(e) for e in solution['error'].values())
    if max_error > 0.01:
        lines.append("")
        lines.append("Error (result - target):")
        lines.append("-" * 30)
        for oxide, err in solution['error'].items():
            if abs(err) > 0.001:
                lines.append(f"  {oxide:8} {err:+.3f}")

    return '\n'.join(lines)


def solve_from_files(target_path, candidates_path, constraints_path=None):
    """
    Main entry point: solve UMF equivalence from file paths.

    Args:
        target_path: path to YAML with target recipe or UMF
        candidates_path: path to YAML with candidate materials
        constraints_path: optional path to YAML with min/max constraints

    Returns:
        solution dict from solve_umf_match()
    """
    candidates = read_materials(candidates_path)
    target_umf = _load_target_umf(target_path, candidates_path)

    constraints = None
    if constraints_path:
        constraints = read_constraints(constraints_path)

    return solve_umf_match(target_umf, candidates, constraints)


def _load_target_umf(path, materials_path=None):
    """
    Load target UMF from a file (recipe or standalone UMF).

    Args:
        path: path to YAML file
        materials_path: optional path to materials file (needed if target is a recipe)

    Returns:
        dict with 'flux' and 'other' oxide dicts
    """
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)

    # Check if it's a standalone UMF (has flux/other keys)
    if 'flux' in data:
        return read_umf(path)

    # Check if it's a recipe file
    if 'recipes' in data:
        recipes = read_recipes(path)
        recipe_id = list(recipes.keys())[0]
        recipe_data = recipes[recipe_id]

        # If recipe has precomputed UMF, use it
        if 'umf' in recipe_data:
            return recipe_data['umf']

        # Otherwise compute UMF from recipe (need materials)
        if materials_path:
            materials = read_materials(materials_path)
            return recipe_to_umf(recipe_data['materials'], materials)

        # Check if materials are in the same file
        if 'materials' in data:
            materials = read_materials(path)
            return recipe_to_umf(recipe_data['materials'], materials)

        raise ValueError("Recipe found but no materials to compute UMF")

    raise ValueError(f"Cannot parse {path} as UMF or recipe")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python solver.py <target.yaml> <candidates.yaml> [constraints.yaml]")
        print()
        print("  target.yaml      - Recipe or UMF to match")
        print("  candidates.yaml  - Materials to use in solution")
        print("  constraints.yaml - Optional min/max constraints per material")
        print()
        print("Constraints format:")
        print("  material_id:")
        print("    min: 20")
        print("    max: 50")
        sys.exit(1)

    target_path = sys.argv[1]
    candidates_path = sys.argv[2]
    constraints_path = sys.argv[3] if len(sys.argv) > 3 else None

    solution = solve_from_files(target_path, candidates_path, constraints_path)

    if solution:
        candidates = read_materials(candidates_path)
        print(format_solution(solution, candidates))
    else:
        print("No solution found")
