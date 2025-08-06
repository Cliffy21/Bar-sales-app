import pandas as pd
from datetime import datetime
import os

DATA_DIR = "reports"
os.makedirs(DATA_DIR, exist_ok=True)

def generate_report(data, expenditure):
    today = datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(DATA_DIR, f"Sales_Report_{today}.xlsx")

    # Calculate total sales per item
    for row in data:
        row['Total Sale'] = row['Quantity Sold'] * row['Price Per Unit']
        row['Stock After'] = row['Stock Before'] - row['Quantity Sold']

    df = pd.DataFrame(data)

    total_income = df['Total Sale'].sum()
    net_income = total_income - expenditure

    summary = {
        "Total Income": total_income,
        "Expenditure": expenditure,
        "Net Income": net_income
    }

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Sales")
        pd.DataFrame([summary]).to_excel(writer, index=False, sheet_name="Summary")

    return filename
