# Selezione dei risultati per la presentazione

Questa selezione riduce i CSV completi a pochi risultati leggibili nelle slide.
I CSV originali restano integri nella stessa cartella.

## Figure consigliate

1. `figures/02_eu_dependency_electricity_trend.png` — andamento UE 2007–2024;
2. `figures/03_shock_2022_gas_price_change.png` — variazione osservata del prezzo del gas nel 2022;
3. `figures/04_ranking_import_dependency_2024.png` — confronto tra Paesi;
4. `figures/05_oil_stock_autonomy_2025.png` — autonomia delle scorte nel 2025;
5. `figures/01_correlation_gpr_electricity.png` — risultato sintetico della correlazione.

La figura `06_import_dependency_gas_price_2024.png` è un'alternativa utile se
si vuole approfondire il confronto household/non-household del gas.

## Righe da citare nelle slide

### Query 1 — correlazione

- Italy: `r = 0,863`, 18 anni confrontabili;
- Ireland: `r = 0,846`;
- Malta: `r = -0,338`.

Interpretazione: associazione lineare osservata, non causalità.

### Query 2 — scorte e media mobile (maggio 2026)

| Paese | Giorni equivalenti | Media mobile 3 mesi |
|-|-:|-:|
| Spain | 106,378 | 102,25 |
| Germany | 92,675 | 93,95 |
| France | 91,343 | 92,23 |
| Italy | 76,592 | 81,17 |

### Query 3 — Italia (2024)

| Dipendenza import | Gas household | Gas non-household |
|-:|-:|-:|
| 73,88% | 0,1173 EUR/kWh | 0,0560 EUR/kWh |

### Query 4 — UE

| Anno | Membri UE | Contributori prezzo | Dipendenza media | Prezzo elettricità |
|-:|-:|-:|-:|-:|
| 2007 | 27 | 26 | 56,79% | 0,0898 EUR/kWh |
| 2020 | 27 | 27 | 57,99% | 0,1077 EUR/kWh |
| 2024 | 27 | 27 | 56,04% | 0,1755 EUR/kWh |

Nel 2019 il conteggio è 28; dal 2020 è 27, coerentemente con la Brexit.
Nel 2007 un Paese membro non ha un'osservazione di prezzo comparabile.

### Query 5 — shock 2022

- Lithuania: `+172,13%`;
- Belgium: `+101,57%`;
- Italy: `+34,43%`.

Il GPR globale passa da `82,07` (2021) a `157,58` (2022) e scende a `121,71`
nel 2023.

### Query 6 — ranking 2024

- Malta: `98,39%`, primo posto;
- Italy: `73,88%`, nono posto;
- Estonia: `4,62%`;
- Norway: `-677,20%`, outlier dovuto alla definizione dell'indicatore Eurostat.

### Query 7 — scorte 2025

- Finland: `150,78` giorni medi;
- Greece: `112,04`;
- Italy: `90,74` giorni medi (min `90,18`, max `91,24`);
- Albania, Georgia, Moldova, Montenegro, North Macedonia, Norway e Türkiye:
  valori medi pari a zero, da presentare esplicitando che sono valori pubblicati
  dalla fonte;
- Serbia: `44,42` giorni medi.

## Set minimo raccomandato

Per una presentazione breve usare le figure 02, 03, 04 e 05, più la tabella
Italia della query 3. La figura 01 può essere aggiunta nella sezione conclusiva
come sintesi quantitativa della relazione GPR-prezzo.
