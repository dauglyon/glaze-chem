#!/bin/bash
# gchem CLI examples
cd "$(dirname "$0")"

echo "=== Calculate UMF for all recipes ==="
gchem umf recipes.yaml materials.yaml

echo ""
echo "=== Calculate UMF for specific recipe ==="
gchem umf recipes.yaml materials.yaml --recipe leach_4321

echo ""
echo "=== Solve for target UMF ==="
gchem solve target.yaml materials.yaml

echo ""
echo "=== Solve with constraints ==="
gchem solve target.yaml materials.yaml constraints.yaml

echo ""
echo "=== Solve from recipe (match its UMF) ==="
gchem solve recipes.yaml materials.yaml --recipe leach_4321

echo ""
echo "=== Calculate UMF with extended flux oxides (Katz) ==="
gchem umf recipes.yaml materials.yaml --recipe leach_4321 --extended

echo ""
echo "=== Calculate CTE (thermal expansion) ==="
gchem cte recipes.yaml materials.yaml

echo ""
echo "=== CTE with verbose breakdown ==="
gchem cte recipes.yaml materials.yaml --recipe leach_4321 --verbose
