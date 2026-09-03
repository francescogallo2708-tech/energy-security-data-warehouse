import os
from pathlib import Path
import pandas as pd

# Percorso del file GPR, risolto rispetto alla radice del repository.
project_dir = Path(__file__).resolve().parents[2]
gpr_file_path = project_dir / "data" / "raw" / "gpr" / "data_gpr_export_202608.xls"

print("=== AVVIO PROFILING DATASET GEOPOLITICAL RISK (GPR) ===\n")

if not os.path.exists(gpr_file_path):
  print(f"[ATTENZIONE] File GPR non trovato nel percorso: {gpr_file_path}")
else:
  print(f"Lettura del file: {os.path.basename(gpr_file_path)}")

  # Lettura del file Excel
  df_gpr = pd.read_excel(gpr_file_path)

  # Dimensioni del dataset
  rows, cols = df_gpr.shape
  print(f"  - Dimensioni totali: {rows} righe, {cols} colonne")

  # Verifica della presenza della colonna temporale principale ('month')
  if "month" in df_gpr.columns:
    min_date = df_gpr["month"].min()
    max_date = df_gpr["month"].max()
    print(f"  - Copertura temporale ('month'): da {min_date} a {max_date}")
  else:
    print(
        "  - [AVVISO] Colonna 'month' non trovata con esattezza nell'intestazione"
        " principale."
    )

  # Statistiche sui valori nulli
  total_cells = rows * cols
  null_cells = df_gpr.isnull().sum().sum()
  print(f"  - Celle totali: {total_cells}")
  print(
      f"  - Celle con valori nulli (NaN): {null_cells}"
      f" ({(null_cells/total_cells)*100:.2f}%)"
  )

  # Anteprima delle principali colonne di indice globale se presenti
  key_indicators = [col for col in ["GPR", "GPRT", "GPRA"] if col in df_gpr.columns]
  if key_indicators:
    print(
        "  - Indicatori globali principali rilevati nel dataset:"
        f" {key_indicators}"
    )

  print("-" * 50)
  print("\nProfiling GPR completato.")
