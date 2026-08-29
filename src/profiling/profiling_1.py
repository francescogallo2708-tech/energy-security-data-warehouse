import os
import pandas as pd

# Percorso della cartella contenente i file raw di Eurostat
eurostat_dir = "Dataset/raw/eurostat"

# Lista dei file TSV Eurostat da profilare
eurostat_files = [
    "nrg_ind_id_tabular.tsv",
    "nrg_pc_202_tabular.tsv",
    "nrg_pc_203_tabular.tsv",
    "nrg_pc_204_tabular.tsv",
    "nrg_pc_205_tabular.tsv",
    "nrg_stk_oem_tabular.tsv",
]

print("=== AVVIO PROFILING DATASET EUROSTAT ===\n")

for filename in eurostat_files:
  file_path = os.path.join(eurostat_dir, filename)

  if not os.path.exists(file_path):
    print(f"[ATTENZIONE] File non trovato: {filename}")
    continue

  print(f"Analisi del file: {filename}")

  # Lettura del file TSV usando il motore python per gestire correttamente i separatori complessi
  df = pd.read_csv(file_path, sep="\t", engine="python")

  # Informazioni generali sulle dimensioni
  num_rows, num_cols = df.shape
  print(f"  - Dimensioni: {num_rows} righe, {num_cols} colonne")

  # La prima colonna contiene i metadati concatenati (es. freq,siec,unit,geo)
  first_col_name = df.columns[0]
  print(f"  - Colonna metadati compositi: '{first_col_name}'")

  # Estrazione di un'anteprima delle componenti splittate per verificare la struttura
  split_sample = df[first_col_name].astype(str).str.split(",", expand=True)
  print(
      f"  - Numero di dimensioni individuate nella prima colonna:"
      f" {split_sample.shape[1]}"
  )

  # Controllo preliminare di valori mancanti o stringhe vuote nelle celle
  missing_count = (df == ": ").sum().sum()
  print(
      f"  - Indicatori di valore mancante (es. ': '): circa {missing_count}"
      " celle"
  )
  print("-" * 50)

print("\nProfiling Eurostat completato.")