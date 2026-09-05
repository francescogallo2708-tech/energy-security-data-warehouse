import os
from pathlib import Path
import pandas as pd

# GPR file path, resolved relative to the repository root.
project_dir = Path(__file__).resolve().parents[2]
gpr_file_path = project_dir / "data" / "raw" / "gpr" / "data_gpr_export_202608.xls"

print("=== STARTING GEOPOLITICAL RISK (GPR) DATASET PROFILING ===\n")

if not os.path.exists(gpr_file_path):
  print(f"[WARNING] GPR file not found at: {gpr_file_path}")
else:
  print(f"Reading file: {os.path.basename(gpr_file_path)}")

  # Read the Excel file.
  df_gpr = pd.read_excel(gpr_file_path)

  # Dataset dimensions.
  rows, cols = df_gpr.shape
  print(f"  - Total dimensions: {rows} rows, {cols} columns")

  # Verify the presence of the primary time column ('month').
  if "month" in df_gpr.columns:
    min_date = df_gpr["month"].min()
    max_date = df_gpr["month"].max()
    print(f"  - Time coverage ('month'): from {min_date} to {max_date}")
  else:
    print(
        "  - [WARNING] Column 'month' was not found exactly in the main"
        " header."
    )

  # Statistics on null values.
  total_cells = rows * cols
  null_cells = df_gpr.isnull().sum().sum()
  print(f"  - Total cells: {total_cells}")
  print(
      f"  - Cells with null values (NaN): {null_cells}"
      f" ({(null_cells/total_cells)*100:.2f}%)"
  )

  # Preview the main global-index columns when present.
  key_indicators = [col for col in ["GPR", "GPRT", "GPRA"] if col in df_gpr.columns]
  if key_indicators:
    print(
        "  - Main global indicators found in the dataset:"
        f" {key_indicators}"
    )

  print("-" * 50)
  print("\nGPR profiling completed.")
