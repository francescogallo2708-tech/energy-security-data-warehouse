# Data sources

This directory contains metadata for the official source datasets used by the
energy-security data warehouse. Raw data files are kept locally and are not
committed by default.

## Eurostat datasets

| Dataset | Role in the project |
|---|---|
| `nrg_ind_id` | Energy import dependency |
| `nrg_stk_oem` | Emergency oil stocks |
| `nrg_pc_202` | Natural gas prices |
| `nrg_pc_203` | Electricity prices |
| `nrg_pc_204` | Energy prices |
| `nrg_pc_205` | Additional energy-price data |

The XML files in this directory provide the corresponding dataset metadata.
Source links and download instructions will be added here as the ETL workflow
is documented.

## Geopolitical Risk

The project also uses the Geopolitical Risk Index as an external source. Its
local data file is intentionally kept outside version control; the source
reference and the procedure used to obtain it will be documented here.
