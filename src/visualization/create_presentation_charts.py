"""Generate presentation-ready charts from the final OLAP query CSV files."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "docs" / "results"
OUTPUT = RESULTS / "figures"
OUTPUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "figure.dpi": 130,
        "savefig.dpi": 220,
        "font.size": 10,
        "axes.titlesize": 14,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
    }
)


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUTPUT / name, bbox_inches="tight")
    plt.close(fig)


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


def correlation_chart() -> None:
    df = load("results_prima_query.csv").sort_values(
        "correlazione_pearson_gpr_prezzo"
    )
    fig, ax = plt.subplots(figsize=(9, 7))
    colors = ["#2f6690" if value >= 0 else "#d1495b" for value in df["correlazione_pearson_gpr_prezzo"]]
    ax.barh(df["paese"], df["correlazione_pearson_gpr_prezzo"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Pearson r (GPR globale annuale vs prezzo elettrico annuale)")
    ax.set_title("Relazione tra rischio geopolitico e prezzo dell'elettricità")
    ax.text(
        0.01,
        -0.08,
        "Valori positivi indicano un'associazione lineare osservata; non implicano causalità.",
        transform=ax.transAxes,
        fontsize=8,
        color="#555555",
    )
    save(fig, "01_correlation_gpr_electricity.png")


def eu_trend_chart() -> None:
    df = load("results_quarta_query.csv").sort_values("anno")
    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    ax2 = ax1.twinx()
    ax1.plot(
        df["anno"],
        df["dipendenza_media_membri_ue_pct"],
        marker="o",
        color="#2f6690",
        label="Dipendenza media (%)",
    )
    ax2.plot(
        df["anno"],
        df["prezzo_medio_elettricita_ue"],
        marker="s",
        color="#d1495b",
        label="Prezzo elettricità (EUR/kWh)",
    )
    ax1.set_xlabel("Anno")
    ax1.set_ylabel("Dipendenza media (%)", color="#2f6690")
    ax2.set_ylabel("Prezzo medio (EUR/kWh)", color="#d1495b")
    ax1.set_title("Evoluzione delle metriche energetiche nell'Unione Europea")
    ax1.axvline(2020, color="#777777", linestyle="--", linewidth=0.9)
    ax1.text(2020.1, ax1.get_ylim()[1] * 0.98, "Brexit: 28 → 27 Paesi", fontsize=8, color="#555555", va="top")
    lines = [ax1.lines[0], ax2.lines[0]]
    ax1.legend(lines, ["Dipendenza media (%)", "Prezzo elettricità (EUR/kWh)"], loc="upper left", frameon=False)
    save(fig, "02_eu_dependency_electricity_trend.png")


def shock_chart() -> None:
    df = load("results_quinta_query.csv")
    shock = df[df["anno"].eq(2022)].copy()
    shock["variazione_prezzo_pct"] = pd.to_numeric(shock["variazione_prezzo_pct"], errors="coerce")
    shock = shock.dropna(subset=["variazione_prezzo_pct"]).sort_values("variazione_prezzo_pct")
    show = pd.concat([shock.head(5), shock.tail(10)]).drop_duplicates().sort_values("variazione_prezzo_pct")
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#d1495b" if value < 0 else "#edae49" for value in show["variazione_prezzo_pct"]]
    ax.barh(show["paese"], show["variazione_prezzo_pct"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("Variazione del prezzo del gas household rispetto al 2021 (%)")
    ax.set_title("Shock del 2022: variazione del prezzo del gas")
    ax.text(
        0.01,
        -0.1,
        "Sono mostrati i principali aumenti e le principali diminuzioni tra i Paesi disponibili.",
        transform=ax.transAxes,
        fontsize=8,
        color="#555555",
    )
    save(fig, "03_shock_2022_gas_price_change.png")


def ranking_chart() -> None:
    df = load("results_sesta_query.csv")
    # Norway is retained in the CSV but its extreme negative value would
    # compress all other countries; show it as a documented outlier instead.
    plotted = df[df["tasso_dipendenza_2024_pct"] > -100]
    top = plotted.head(10).sort_values("tasso_dipendenza_2024_pct")
    bottom = plotted.tail(5).sort_values("tasso_dipendenza_2024_pct")
    show = pd.concat([bottom, top]).drop_duplicates().sort_values("tasso_dipendenza_2024_pct")
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#d1495b" if value < 0 else "#2f6690" for value in show["tasso_dipendenza_2024_pct"]]
    ax.barh(show["paese"], show["tasso_dipendenza_2024_pct"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("Tasso di dipendenza dalle importazioni (%)")
    ax.set_title("Ranking della dipendenza energetica nel 2024")
    ax.text(
        0.01,
        -0.1,
        "Top 10 e ultimi 5 Paesi; la Norvegia (-677,20%) è un outlier Eurostat escluso dalla scala del grafico.",
        transform=ax.transAxes,
        fontsize=8,
        color="#555555",
    )
    save(fig, "04_ranking_import_dependency_2024.png")


def stocks_chart() -> None:
    df = load("results_settima_query.csv")
    df = df[df["anno"].eq(2025)].sort_values("giorni_equivalenti_medi")
    show = pd.concat([df.head(5), df.tail(10)]).drop_duplicates().sort_values("giorni_equivalenti_medi")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(show["paese"], show["giorni_equivalenti_medi"], color="#2a9d8f")
    ax.set_xlabel("Giorni equivalenti medi")
    ax.set_title("Autonomia delle scorte petrolifere nel 2025")
    ax.text(
        0.01,
        -0.1,
        "Top 10 e ultimi 5 Paesi; media annuale dei valori mensili disponibili.",
        transform=ax.transAxes,
        fontsize=8,
        color="#555555",
    )
    save(fig, "05_oil_stock_autonomy_2025.png")


def gas_dependency_chart() -> None:
    df = load("results_terza_query.csv")
    df = df[df["anno"].eq(2024)].copy()
    for column in ["tasso_dipendenza_import_pct", "prezzo_gas_household", "prezzo_gas_non_household"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["tasso_dipendenza_import_pct"])
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(
        df["tasso_dipendenza_import_pct"],
        df["prezzo_gas_household"],
        color="#2f6690",
        label="Household",
        alpha=0.85,
    )
    ax.scatter(
        df["tasso_dipendenza_import_pct"],
        df["prezzo_gas_non_household"],
        color="#edae49",
        label="Non-household",
        alpha=0.85,
    )
    italy = df[df["paese"].eq("Italy")]
    if not italy.empty:
        row = italy.iloc[0]
        ax.annotate("Italy", (row["tasso_dipendenza_import_pct"], row["prezzo_gas_household"]), xytext=(6, 6), textcoords="offset points")
    ax.set_xlabel("Dipendenza dalle importazioni (%)")
    ax.set_ylabel("Prezzo del gas (EUR/kWh)")
    ax.set_title("Dipendenza energetica e prezzi del gas — 2024")
    ax.legend(frameon=False)
    save(fig, "06_import_dependency_gas_price_2024.png")


if __name__ == "__main__":
    correlation_chart()
    eu_trend_chart()
    shock_chart()
    ranking_chart()
    stocks_chart()
    gas_dependency_chart()
    print(f"Generate 6 charts in: {OUTPUT}")
