# Result selection for the presentation

This selection reduces the complete CSV files to a small number of results
that can be read easily on slides. The original CSV files remain unchanged in
the same directory.

## Recommended figures

1. `figures/02_eu_dependency_electricity_trend.png` — EU trend, 2007–2024;
2. `figures/03_shock_2022_gas_price_change.png` — observed gas-price variation in 2022;
3. `figures/04_ranking_import_dependency_2024.png` — comparison across countries;
4. `figures/05_oil_stock_autonomy_2025.png` — oil-stock autonomy in 2025;
5. `figures/01_correlation_gpr_electricity.png` — summary correlation result.

`06_import_dependency_gas_price_2024.png` is a useful alternative figure for a
more detailed comparison of household and non-household gas prices.

## Rows to cite in the slides

### Query 1 — correlation

- Italy: `r = 0.863`, 18 comparable years;
- Ireland: `r = 0.846`;
- Malta: `r = -0.338`.

Interpretation: observed linear association, not causality.

### Query 2 — oil stocks and moving average (May 2026)

| Country | Equivalent days | Three-month moving average |
|-|-:|-:|
| Spain | 106.378 | 102.25 |
| Germany | 92.675 | 93.95 |
| France | 91.343 | 92.23 |
| Italy | 76.592 | 81.17 |

### Query 3 — Italy (2024)

| Import dependency | Household gas | Non-household gas |
|-:|-:|-:|
| 73.88% | 0.1173 EUR/kWh | 0.0560 EUR/kWh |

### Query 4 — EU

| Year | EU members | Price contributors | Average dependency | Electricity price |
|-:|-:|-:|-:|-:|
| 2007 | 27 | 26 | 56.79% | 0.0898 EUR/kWh |
| 2020 | 27 | 27 | 57.99% | 0.1077 EUR/kWh |
| 2024 | 27 | 27 | 56.04% | 0.1755 EUR/kWh |

In 2019 the count is 28; from 2020 it is 27, consistently with Brexit.
In 2007, one member country has no comparable price observation.

### Query 5 — 2022 shock

- Lithuania: `+172.13%`;
- Belgium: `+101.57%`;
- Italy: `+34.43%`.

Global GPR rises from `82.07` (2021) to `157.58` (2022) and decreases to
`121.71` in 2023.

### Query 6 — 2024 ranking

- Malta: `98.39%`, first place;
- Italy: `73.88%`, ninth place;
- Estonia: `4.62%`;
- Norway: `-677.20%`, an outlier caused by the Eurostat indicator definition.

### Query 7 — 2025 oil stocks

- Finland: `150.78` average days;
- Greece: `112.04`;
- Italy: `90.74` average days (min `90.18`, max `91.24`);
- Albania, Georgia, Moldova, Montenegro, North Macedonia, Norway, and Türkiye:
  average values equal to zero, which should be presented explicitly as values
  published by the source;
- Serbia: `44.42` average days.

## Recommended minimum set

For a short presentation, use Figures 02, 03, 04, and 05, together with the
Italy table from Query 3. Figure 01 can be added in the conclusion as a
quantitative summary of the GPR-price relationship.
