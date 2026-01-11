import pandas as pd

from bachelorarbeit.config import REPORTS_DIR


def write_benchmarks(df, cfg, cfg_name, cfg_title):
    # === CHARTS FOR OVERLEAF/LATEX ===
    # === score vs difficulty ===
    export_csv(
        df,
        [
            ("ilp", "courses"),
            ("ilp", "score"),
            ("ilp_gpu", "score"),
            ("hill_climbing_v1", "score"),
            ("hill_climbing_v3", "score"),
            ("offering_order", "score"),
        ],
        [
            "difficulty",
            "ILP",
            "ILP GPU" "Hill Climbing v1",
            "Hill Climbing v3",
            "Offering Order",
        ],
        REPORTS_DIR / f"csv/score_diff__{cfg_name}.csv",
    )

    # === running time vs difficulty ===
    export_csv(
        df,
        [
            ("ilp", "courses"),
            ("ilp", "timings_mean"),
            ("ilp", "timings_stdev"),
            ("ilp_gpu", "timings_mean"),
            ("ilp_gpu", "timings_stdev"),
            ("hill_climbing_v1", "timings_mean"),
            ("hill_climbing_v1", "timings_stdev"),
            ("hill_climbing_v3", "timings_mean"),
            ("hill_climbing_v3", "timings_stdev"),
            ("offering_order", "timings_mean"),
            ("offering_order", "timings_stdev"),
        ],
        [
            "difficulty",
            "ILP",
            "ILP stdev",
            "ILP GPU",
            "ILP GPU stdev",
            "Hill Climbing v1",
            "Hill Climbing v1 stdev",
            "Hill Climbing v3",
            "Hill Climbing v3 stdev",
            "Offering Order",
            "Offering Order stdev",
        ],
        REPORTS_DIR / f"csv/timing_diff__{cfg_name}.csv",
    )

    # === running time vs difficulty ===
    export_csv(
        df,
        [
            ("ilp", "courses"),
            ("ilp", "memory_mean"),
            ("ilp", "memory_stdev"),
            ("ilp_gpu", "memory_mean"),
            ("ilp_gpu", "memory_stdev"),
            ("hill_climbing_v1", "memory_mean"),
            ("hill_climbing_v1", "memory_stdev"),
            ("hill_climbing_v3", "memory_mean"),
            ("hill_climbing_v3", "memory_stdev"),
            ("offering_order", "memory_mean"),
            ("offering_order", "memory_stdev"),
        ],
        [
            "difficulty",
            "ILP",
            "ILP stdev",
            "ILP GPU",
            "ILP GPU stdev",
            "Hill Climbing v1",
            "Hill Climbing v1 stdev",
            "Hill Climbing v3",
            "Hill Climbing v3 stdev",
            "Offering Order",
            "Offering Order stdev",
        ],
        REPORTS_DIR / f"csv/memory_diff__{cfg_name}.csv",
    )

    # === CHARTS IN XLSX ===
    out_path = REPORTS_DIR / f"xlsx/benchmark_{cfg_name}.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        header_lines = [f"Benchmark Constraints {cfg_title}"]
        for k, v in cfg.items():
            header_lines.append(f"{k}: {v}")
        header_df = pd.DataFrame(header_lines, columns=["info"])
        header_df.to_excel(
            writer, sheet_name="results", index=False, header=False
        )

        startrow = len(header_lines) + 2
        df.to_excel(writer, sheet_name="results", startrow=startrow)


def export_csv(df, columns, newColumnNames, file):
    df_stat = df[columns].copy()
    df_stat.columns = newColumnNames
    df_stat = df_stat.fillna("nan")  # Replace None/NaN with "nan"
    df_stat.to_csv(file, index=False, sep=",")
