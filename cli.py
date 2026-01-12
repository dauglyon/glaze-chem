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


if __name__ == "__main__":
    app()
