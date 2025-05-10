#!/usr/bin/env python3
import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate a PDF report from a SAT-attack CSV results file."
    )
    p.add_argument(
        "-i", "--input-csv",
        type=Path,
        default=Path("results/sat_attack_parallel_results.csv"),
        help="Path to the input CSV file"
    )
    p.add_argument(
        "-o", "--output-pdf",
        type=Path,
        default=Path("results/sat_attack_summary.pdf"),
        help="Path where the PDF report will be written"
    )
    p.add_argument(
        "--rows-per-page",
        type=int,
        default=30,
        help="Number of table rows per PDF page"
    )
    return p.parse_args()


def load_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    return pd.read_csv(csv_path)


def render_table_pages(df: pd.DataFrame, pdf_path: Path, rows_per_page: int):
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(pdf_path) as pdf:
        total_rows = len(df)
        num_pages = (total_rows + rows_per_page - 1) // rows_per_page

        for page in range(num_pages):
            start = page * rows_per_page
            end = min(start + rows_per_page, total_rows)
            slice_df = df.iloc[start:end]

            fig, ax = plt.subplots(
                figsize=(11, 8.5),  # US Letter landscape
            )
            ax.axis("off")

            table = ax.table(
                cellText=slice_df.values,
                colLabels=slice_df.columns,
                cellLoc="center",
                loc="center"
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1.1, 1.1)

            title = f"Fred IoT Security Assignment (Rows {start+1}–{end})"
            ax.set_title(title, fontsize=12, pad=12)

            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)


def main():
    args = parse_args()
    df = load_data(args.input_csv)
    render_table_pages(df, args.output_pdf, args.rows_per_page)
    print(f"PDF report generated: {args.output_pdf}")


if __name__ == "__main__":
    main()
