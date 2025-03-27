import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os

# File paths
csv_path = "results/sat_attack_parallel_results.csv"
pdf_path = "results/sat_attack_summary.pdf"

# Ensure the CSV exists
if not os.path.exists(csv_path):
    raise FileNotFoundError(f"CSV file not found: {csv_path}")

# Load CSV data
df = pd.read_csv(csv_path)

# Generate PDF
with PdfPages(pdf_path) as pdf:
    fig, ax = plt.subplots(figsize=(14, min(0.5 * len(df), 25)))
    ax.axis('off')
    table = ax.table(cellText=df.values,
                     colLabels=df.columns,
                     cellLoc='center',
                     loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.2, 1.2)
    # Centered title
    ax.set_title("Fred IoT security Assignement", fontsize=13, pad=20, loc='center')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

print(f"PDF report generated successfully: {pdf_path}")
