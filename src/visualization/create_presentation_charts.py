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
    df = load("query_01_gpr_electricity_correlation.csv").sort_values(
        "pearson_correlation_gpr_price"
    )
    fig, ax = plt.subplots(figsize=(9, 7))
    colors = ["#2f6690" if value >= 0 else "#d1495b" for value in df["pearson_correlation_gpr_price"]]
    ax.barh(df["country"], df["pearson_correlation_gpr_price"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Pearson r (annual global GPR vs annual electricity price)")
    ax.set_title("Relationship between geopolitical risk and electricity prices")
    ax.text(
        0.01,
        -0.08,
        "Positive values indicate an observed linear association; they do not imply causality.",
        transform=ax.transAxes,
        fontsize=8,
        color="#555555",
    )
    save(fig, "01_correlation_gpr_electricity.png")


def eu_trend_chart() -> None:
    df = load("query_04_eu_dependency_electricity.csv").sort_values("year")
    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    ax2 = ax1.twinx()
    ax1.plot(
        df["year"],
        df["average_eu_import_dependency_pct"],
        marker="o",
        color="#2f6690",
        label="Average dependency (%)",
    )
    ax2.plot(
        df["year"],
        df["average_eu_electricity_price"],
        marker="s",
        color="#d1495b",
        label="Electricity price (EUR/kWh)",
    )
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Average dependency (%)", color="#2f6690")
    ax2.set_ylabel("Average price (EUR/kWh)", color="#d1495b")
    ax1.set_title("Evolution of energy metrics in the European Union")
    ax1.axvline(2020, color="#777777", linestyle="--", linewidth=0.9)
    ax1.text(2020.1, ax1.get_ylim()[1] * 0.98, "Brexit: 28 → 27 countries", fontsize=8, color="#555555", va="top")
    lines = [ax1.lines[0], ax2.lines[0]]
    ax1.legend(lines, ["Average dependency (%)", "Electricity price (EUR/kWh)"], loc="upper left", frameon=False)
    save(fig, "02_eu_dependency_electricity_trend.png")


def shock_chart() -> None:
    df = load("query_05_gpr_gas_price_variation.csv")
    shock = df[df["year"].eq(2022)].copy()
    shock["gas_price_variation_pct"] = pd.to_numeric(shock["gas_price_variation_pct"], errors="coerce")
    shock = shock.dropna(subset=["gas_price_variation_pct"]).sort_values("gas_price_variation_pct")
    show = pd.concat([shock.head(5), shock.tail(10)]).drop_duplicates().sort_values("gas_price_variation_pct")
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#d1495b" if value < 0 else "#edae49" for value in show["gas_price_variation_pct"]]
    ax.barh(show["country"], show["gas_price_variation_pct"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("Household gas-price variation relative to 2021 (%)")
    ax.set_title("Observed gas-price variation in 2022")
    ax.text(
        0.01,
        -0.1,
        "Temporal comparison, not evidence of a causal relationship. The main increases and decreases are shown.",
        transform=ax.transAxes,
        fontsize=8,
        color="#555555",
    )
    save(fig, "03_shock_2022_gas_price_change.png")


def ranking_chart() -> None:
    df = load("query_06_import_dependency_ranking.csv")
    # Norway is retained in the CSV but its extreme negative value would
    # compress all other countries; show it as a documented outlier instead.
    plotted = df[df["import_dependency_rate_2024_pct"] > -100]
    top = plotted.head(10).sort_values("import_dependency_rate_2024_pct")
    bottom = plotted.tail(5).sort_values("import_dependency_rate_2024_pct")
    show = (
        pd.concat([bottom, top])
        .drop_duplicates()
        .sort_values("import_dependency_rate_2024_pct")
    )
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = [
        "#d1495b" if value < 0 else "#2f6690"
        for value in show["import_dependency_rate_2024_pct"]
    ]
    ax.barh(show["country"], show["import_dependency_rate_2024_pct"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("Import dependency rate (%)")
    ax.set_title("Energy-dependency ranking in 2024")
    ax.text(
        0.01,
        -0.1,
        "Top 10 and bottom 5 countries; Norway (-677.20%) is a Eurostat outlier excluded from the chart scale.",
        transform=ax.transAxes,
        fontsize=8,
        color="#555555",
    )
    save(fig, "04_ranking_import_dependency_2024.png")


def stocks_chart() -> None:
    df = load("query_07_oil_stock_autonomy.csv")
    df = df[df["year"].eq(2025)].sort_values("average_equivalent_days")
    zero_values = df[df["average_equivalent_days"].eq(0)].sort_values("country")
    non_zero_values = df[~df["average_equivalent_days"].eq(0)].tail(10)
    show = pd.concat([zero_values, non_zero_values]).drop_duplicates().sort_values("average_equivalent_days")
    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.barh(show["country"], show["average_equivalent_days"], color="#2a9d8f")
    for bar, value in zip(bars, show["average_equivalent_days"]):
        if value == 0:
            ax.text(
                0.8,
                bar.get_y() + bar.get_height() / 2,
                "0",
                va="center",
                ha="left",
                fontsize=8,
                color="#333333",
            )
    ax.set_xlabel("Average equivalent days")
    ax.set_title("Oil-stock autonomy in 2025")
    ax.text(
        0.01,
        -0.1,
        "Top 10 non-zero values; the seven countries with a value of 0 are explicitly labelled.",
        transform=ax.transAxes,
        fontsize=8,
        color="#555555",
    )
    save(fig, "05_oil_stock_autonomy_2025.png")


def gas_dependency_chart() -> None:
    df = load("query_03_import_dependency_gas_prices.csv")
    df = df[df["year"].eq(2024)].copy()
    for column in ["import_dependency_rate_pct", "household_gas_price", "non_household_gas_price"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["import_dependency_rate_pct"])
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(
        df["import_dependency_rate_pct"],
        df["household_gas_price"],
        color="#2f6690",
        label="Household",
        alpha=0.85,
    )
    ax.scatter(
        df["import_dependency_rate_pct"],
        df["non_household_gas_price"],
        color="#edae49",
        label="Non-household",
        alpha=0.85,
    )
    italy = df[df["country"].eq("Italy")]
    if not italy.empty:
        row = italy.iloc[0]
        ax.annotate("Italy", (row["import_dependency_rate_pct"], row["household_gas_price"]), xytext=(6, 6), textcoords="offset points")
    ax.set_xlabel("Import dependency rate (%)")
    ax.set_ylabel("Gas price (EUR/kWh)")
    ax.set_title("Energy dependency and gas prices — 2024")
    ax.legend(frameon=False)
    save(fig, "06_import_dependency_gas_price_2024.png")


if __name__ == "__main__":
    correlation_chart()
    eu_trend_chart()
    shock_chart()
    ranking_chart()
    stocks_chart()
    gas_dependency_chart()
    print(f"Generated 6 charts in: {OUTPUT}")
