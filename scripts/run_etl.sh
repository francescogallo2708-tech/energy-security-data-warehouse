#!/usr/bin/env bash
# ==============================================================================
# ETL Runner for macOS / Linux
# Energy Security Data Warehouse
# ==============================================================================

set -euo pipefail

# Configuration with fallback to environment variables or defaults
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5433}"
export PGDATABASE="${PGDATABASE:-energy_gpr_dw}"
export PGUSER="${PGUSER:-postgres}"

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=================================================="
echo "Energy Security Data Warehouse - ETL Pipeline"
echo "Database: $PGDATABASE on $PGHOST:$PGPORT"
echo "User:     $PGUSER"
echo "=================================================="

# Detect python executable
PYTHON_CMD="python3"
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    PYTHON_CMD="python"
fi

# Ordered sequence of ETL scripts
ETL_SCRIPTS=(
    "src/etl/etl_load_time.py"
    "src/etl/etl_load_geo.py"
    "src/etl/etl_load_bridge_eu.py"
    "src/etl/etl_load_gpr.py"
    "src/etl/etl_load_import_dep.py"
    "src/etl/etl_load_energy_prices.py"
    "src/etl/etl_load_oil_stocks.py"
)

for script in "${ETL_SCRIPTS[@]}"; do
    echo ""
    echo ">>> Running $PYTHON_CMD $script"
    "$PYTHON_CMD" "$script"
done

echo ""
echo "=================================================="
echo "All ETL scripts completed successfully!"
echo "Next: run sql/schema/verify_final_dw.sql"
echo "=================================================="
