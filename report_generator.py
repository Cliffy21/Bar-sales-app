import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import json

DATA_DIR = "reports"
ANALYTICS_DIR = "analytics"
CONFIG_FILE = "bar_config.json"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ANALYTICS_DIR, exist_ok=True)

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"bar_name": "Your Bar Name", "tax_rate": 0.16, "currency": "Ksh"}

def create_styled_header(ws, headers, row_num=1):
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=12)
    header_alignment = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row_num, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = border

def style_data_cells(ws, start_row, end_row, start_col, end_col):
    data_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    data_font = Font(size=10)
    data_alignment = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    for row in range(start_row, end_row + 1):
        for col in range(start_col, end_col + 1):
            cell = ws.cell(row=row, column=col)
            if row % 2 == 0:
                cell.fill = data_fill
            cell.font = data_font
            cell.alignment = data_alignment
            cell.border = border

def generate_report(data, expenditure):
    config = load_config()
    today = datetime.now()
    filename = os.path.join(DATA_DIR, f"Sales_Report_{today.strftime('%Y%m%d_%H%M%S')}.xlsx")

    wb = Workbook()
    wb.remove(wb.active)
    
    # Sales Summary Sheet
    ws_summary = wb.create_sheet("Sales Summary")
    ws_summary['A1'] = f"{config['bar_name']} - Daily Sales Report"
    ws_summary['A1'].font = Font(size=16, bold=True, color="366092")
    ws_summary['A2'] = f"Date: {today.strftime('%A, %B %d, %Y')}"
    ws_summary['A2'].font = Font(size=12, italic=True)

    headers = ["Product", "Category", "Subcategory", "Stock Before", "Qty Sold", "Price", "Total", "Stock After"]
    create_styled_header(ws_summary, headers, 4)
    
    for i, row in enumerate(data, 5):
        ws_summary[f'A{i}'] = row["Product Name"]
        ws_summary[f'B{i}'] = row.get("Category", "")
        ws_summary[f'C{i}'] = row.get("Subcategory", "")
        ws_summary[f'D{i}'] = row["Stock Before"]
        ws_summary[f'E{i}'] = row["Quantity Sold"]
        ws_summary[f'F{i}'] = row["Price Per Unit"]
        ws_summary[f'G{i}'] = row["Total Sale"]
        ws_summary[f'H{i}'] = row["Stock After"]

    if data:
        style_data_cells(ws_summary, 5, 4 + len(data), 1, 8)

    total_row = 5 + len(data)
    ws_summary[f'A{total_row}'] = "TOTALS"
    ws_summary[f'A{total_row}'].font = Font(bold=True)
    ws_summary[f'E{total_row}'] = sum(row["Quantity Sold"] for row in data)
    ws_summary[f'G{total_row}'] = sum(row["Total Sale"] for row in data)
    
    total_fill = PatternFill(start_color="FFE699", end_color="FFE699", fill_type="solid")
    for col in range(1, 9):
        cell = ws_summary.cell(row=total_row, column=col)
        cell.fill = total_fill
        cell.font = Font(bold=True)

    # Financial Summary Sheet
    ws_financial = wb.create_sheet("Financial Summary")
    total_income = sum(row["Total Sale"] for row in data)
    tax_amount = total_income * config.get('tax_rate', 0.16)
    net_income = total_income - expenditure - tax_amount
    
    financial_data = [
        ["Metric", "Amount (Ksh)", "Percentage"],
        ["Gross Revenue", total_income, "100%"],
        ["Less: Expenditure", expenditure, f"{(expenditure/total_income*100):.1f}%" if total_income > 0 else "0%"],
        ["Less: Tax (VAT)", tax_amount, f"{(tax_amount/total_income*100):.1f}%" if total_income > 0 else "0%"],
        ["Net Profit", net_income, f"{(net_income/total_income*100):.1f}%" if total_income > 0 else "0%"]
    ]
    
    ws_financial['A1'] = "Financial Summary"
    ws_financial['A1'].font = Font(size=16, bold=True, color="366092")
    create_styled_header(ws_financial, financial_data[0], 3)
    
    for i, row in enumerate(financial_data[1:], 4):
        ws_financial[f'A{i}'] = row[0]
        ws_financial[f'B{i}'] = row[1]
        ws_financial[f'C{i}'] = row[2]
    
    style_data_cells(ws_financial, 4, 3 + len(financial_data), 1, 3)

    # Auto-adjust column widths
    for ws in wb.worksheets:
        for column in ws.columns:
            max_length = max(len(str(cell.value)) for cell in column)
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column[0].column_letter].width = adjusted_width

    wb.save(filename)
    save_analytics_data(data, expenditure, total_income, net_income)
    return filename

def save_analytics_data(sales_data, expenditure, total_income, net_income):
    analytics_file = os.path.join(ANALYTICS_DIR, "daily_analytics.json")
    
    try:
        with open(analytics_file, 'r') as f:
            analytics = json.load(f)
    except FileNotFoundError:
        analytics = []
    
    today_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_income": total_income,
        "expenditure": expenditure,
        "net_income": net_income,
        "total_items_sold": sum(row["Quantity Sold"] for row in sales_data),
        "products_sold": len([row for row in sales_data if row["Quantity Sold"] > 0])
    }
    
    analytics = [entry for entry in analytics if entry["date"] != today_data["date"]]
    analytics.append(today_data)
    analytics = sorted(analytics, key=lambda x: x["date"])[-30:]
    
    with open(analytics_file, 'w') as f:
        json.dump(analytics, f, indent=2)