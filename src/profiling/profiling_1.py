import os
from pathlib import Path
import pandas as pd

# Path to the directory containing raw Eurostat files.
project_dir = Path(__file__).resolve().parents[2]
eurostat_dir = project_dir / "data" / "raw" / "eurostat"

# List of Eurostat TSV files to profile.
eurostat_files = [
    "nrg_ind_id_tabular.tsv",
    "nrg_pc_202_tabular.tsv",
    "nrg_pc_203_tabular.tsv",
    "nrg_pc_204_tabular.tsv",
    "nrg_pc_205_tabular.tsv",
    "nrg_stk_oem_tabular.tsv",
]

print("=== STARTING EUROSTAT DATASET PROFILING ===\n")

for filename in eurostat_files:
  file_path = eurostat_dir / filename

  if not os.path.exists(file_path):
    print(f"[WARNING] File not found: {filename}")
    continue

  print(f"Analysing file: {filename}")

  # Read the TSV file with the Python engine to handle complex separators.
  df = pd.read_csv(file_path, sep="\t", engine="python")

  # General size information.
  num_rows, num_cols = df.shape
  print(f"  - Dimensions: {num_rows} rows, {num_cols} columns")

  # The first column contains concatenated metadata (e.g., freq,siec,unit,geo).
  first_col_name = df.columns[0]
  print(f"  - Composite metadata column: '{first_col_name}'")

  # Extract a preview of split components to verify the structure.
  split_sample = df[first_col_name].astype(str).str.split(",", expand=True)
  print(
      f"  - Number of dimensions identified in the first column:"
      f" {split_sample.shape[1]}"
  )

  # Preliminary check for missing values or empty strings in cells.
  missing_count = (df == ": ").sum().sum()
  print(
      f"  - Missing-value markers (e.g., ': '): approximately {missing_count}"
      " cells"
  )
  print("-" * 50)

print("\nEurostat profiling completed.")
