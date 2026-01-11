# UMF Calculations for Ceramic Glazes

Educational Jupyter notebooks explaining Unity Molecular Formula (UMF) calculations for ceramic glaze chemistry.

## Notebooks

1. **[umf_calculations.ipynb](umf_calculations.ipynb)** - Fundamentals of UMF: what it is, how to calculate it from oxide percentages, and how to interpret the results.

2. **[recipe_to_umf.ipynb](recipe_to_umf.ipynb)** - Going from a glaze recipe (materials and amounts) to UMF. Covers combining material analyses and handling LOI.

3. **[ingredient_substitution.ipynb](ingredient_substitution.ipynb)** - Using UMF to substitute materials while maintaining glaze chemistry.

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
