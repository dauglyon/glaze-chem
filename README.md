# UMF Calculations for Ceramic Glazes

Educational Jupyter notebooks and CLI tools for Unity Molecular Formula (UMF) calculations in ceramic glaze chemistry.

## CLI

```bash
uv sync
uv run gchem --help
```

Commands:
- `gchem umf` - Calculate UMF from recipe
- `gchem solve` - Find recipe matching target UMF
- `gchem cte` - Calculate thermal expansion
- `gchem blend` - Generate N-axial blend grids

See `cli-example/` for sample files.

## Notebooks

1. **[umf_calculations.ipynb](umf_calculations.ipynb)** - Fundamentals of UMF: what it is, how to calculate it from oxide percentages, and how to interpret the results.

2. **[recipe_to_umf.ipynb](recipe_to_umf.ipynb)** - Going from a glaze recipe (materials and amounts) to UMF. Covers combining material analyses and handling LOI.

3. **[ingredient_substitution.ipynb](ingredient_substitution.ipynb)** - Using UMF to substitute materials while maintaining glaze chemistry.

4. **[solver_examples.ipynb](solver_examples.ipynb)** - UMF matching solver examples.

## Setup

Requires Python 3.13+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run jupyter lab
```

## Format Library

`utils.py` provides YAML-based storage for materials, recipes, and UMF data:

```yaml
materials:
  whiting:
    name: Whiting
    loi: 44.0
    analysis:
      CaO: 56.0

recipes:
  cone10_clear:
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
```
