"""
CLI for glaze chemistry calculations.
"""

import sys
from pathlib import Path
from typing import Optional

import click
import typer
from typer.core import TyperGroup

# Use plain click formatting instead of rich
class PlainGroup(TyperGroup):
    def format_help(self, ctx, formatter):
        click.Group.format_help(self, ctx, formatter)

from solver import (
    solve_umf_match, recipe_to_umf, format_solution,
    FLUX_TRADITIONAL, FLUX_EXTENDED
)
from utils import read_materials, read_recipes, read_umf, read_constraints, format_umf_table
from cte import calculate_cte, format_cte
from blend import generate_blends, format_blends


app = typer.Typer(
    cls=PlainGroup,
    add_completion=False,
    pretty_exceptions_enable=False,
    no_args_is_help=True,
    rich_markup_mode=None
)


def _load_target(path: Path, materials_path: Path, recipe_id: Optional[str], flux_oxides):
    """Load target UMF from a file (UMF or recipe)."""
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)

    # Standalone UMF
    if 'flux' in data:
        return read_umf(path)

    # Recipe file
    if 'recipes' in data:
        recipes = read_recipes(path)
        if recipe_id:
            if recipe_id not in recipes:
                print(f"Recipe '{recipe_id}' not found. Available: {list(recipes.keys())}")
                raise typer.Exit(1)
            recipe_data = recipes[recipe_id]
        else:
            recipe_id = list(recipes.keys())[0]
            recipe_data = recipes[recipe_id]

        if 'umf' in recipe_data:
            return recipe_data['umf']

        materials = read_materials(materials_path)
        return recipe_to_umf(recipe_data['materials'], materials, flux_oxides)

    print(f"Cannot parse {path} as UMF or recipe")
    raise typer.Exit(1)


@app.command()
def solve(
    target: Path = typer.Argument(..., help="Target UMF or recipe file"),
    materials: Path = typer.Argument(..., help="Candidate materials file"),
    constraints: Optional[Path] = typer.Argument(None, help="Constraints file"),
    recipe: Optional[str] = typer.Option(None, "--recipe", "-r", help="Recipe ID if target has multiple"),
    extended: bool = typer.Option(False, "--extended", "-e", help="Use extended UMF (Katz)")
):
    """Find recipe matching target UMF."""
    flux_oxides = FLUX_EXTENDED if extended else FLUX_TRADITIONAL

    target_umf = _load_target(target, materials, recipe, flux_oxides)
    candidates = read_materials(materials)

    constraint_dict = None
    if constraints:
        constraint_dict = read_constraints(constraints)

    solution = solve_umf_match(target_umf, candidates, constraint_dict, flux_oxides)

    if solution:
        print(format_solution(solution, candidates))
    else:
        print("No solution found")
        raise typer.Exit(1)


@app.command()
def umf(
    recipes_file: Path = typer.Argument(..., help="Recipe file"),
    materials: Path = typer.Argument(..., help="Materials file"),
    recipe: Optional[str] = typer.Option(None, "--recipe", "-r", help="Recipe ID (omit for all)"),
    extended: bool = typer.Option(False, "--extended", "-e", help="Use extended UMF (Katz)")
):
    """Calculate UMF from recipe."""
    flux_oxides = FLUX_EXTENDED if extended else FLUX_TRADITIONAL

    recipes = read_recipes(recipes_file)
    mats = read_materials(materials)

    if recipe:
        if recipe not in recipes:
            print(f"Recipe '{recipe}' not found. Available: {list(recipes.keys())}")
            raise typer.Exit(1)
        recipe_ids = [recipe]
    else:
        recipe_ids = list(recipes.keys())

    for i, rid in enumerate(recipe_ids):
        recipe_data = recipes[rid]
        result = recipe_to_umf(recipe_data['materials'], mats, flux_oxides)

        if len(recipe_ids) > 1:
            name = recipe_data.get('name', rid)
            print(f"{name}:")
            print("-" * 30)

        print(format_umf_table(result))

        if i < len(recipe_ids) - 1:
            print()


@app.command()
def cte(
    recipes_file: Path = typer.Argument(..., help="Recipe file"),
    materials: Path = typer.Argument(..., help="Materials file"),
    recipe: Optional[str] = typer.Option(None, "--recipe", "-r", help="Recipe ID (omit for all)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show oxide contributions")
):
    """Calculate coefficient of thermal expansion."""
    recipes = read_recipes(recipes_file)
    mats = read_materials(materials)

    if recipe:
        if recipe not in recipes:
            print(f"Recipe '{recipe}' not found. Available: {list(recipes.keys())}")
            raise typer.Exit(1)
        recipe_ids = [recipe]
    else:
        recipe_ids = list(recipes.keys())

    for i, rid in enumerate(recipe_ids):
        recipe_data = recipes[rid]
        result = calculate_cte(recipe_data['materials'], mats)

        if len(recipe_ids) > 1:
            name = recipe_data.get('name', rid)
            print(f"{name}:")

        print(format_cte(result, verbose))

        if i < len(recipe_ids) - 1:
            print()


@app.command()
def blend(
    recipes_file: Path = typer.Argument(..., help="Recipe file with corner recipes"),
    materials: Path = typer.Argument(..., help="Materials file"),
    corners: list[str] = typer.Option(..., "--from", "-f", help="Recipe IDs to blend (2+ corners)"),
    steps: int = typer.Option(5, "--steps", "-s", help="Number of steps along each edge"),
    extended: bool = typer.Option(False, "--extended", "-e", help="Use extended UMF (Katz)")
):
    """Generate N-axial blend grid from corner recipes."""
    flux_oxides = FLUX_EXTENDED if extended else FLUX_TRADITIONAL

    recipes = read_recipes(recipes_file)
    mats = read_materials(materials)

    if len(corners) < 2:
        print("Need at least 2 corners for a blend")
        raise typer.Exit(1)

    # Validate corner recipes exist
    corner_recipes = []
    for corner_id in corners:
        if corner_id not in recipes:
            print(f"Recipe '{corner_id}' not found. Available: {list(recipes.keys())}")
            raise typer.Exit(1)
        corner_recipes.append(recipes[corner_id]['materials'])

    blends = generate_blends(corner_recipes, corners, steps, mats, flux_oxides)
    print(format_blends(blends, mats))


if __name__ == "__main__":
    app()
