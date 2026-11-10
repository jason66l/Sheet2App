"""Rebuild samples/Event_Budget_2026.xlsx from the design mockups.

Real formulas on the Budget sheet, then a LibreOffice recalc so the file also
carries Excel-style cached values (needed for openpyxl data_only=True and for
the reconciliation check). Members sheet contents are invented placeholders.
"""

import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).resolve().parents[1] / "samples" / "Event_Budget_2026.xlsx"
BOLD = Font(bold=True)
HDR = PatternFill("solid", fgColor="EAF1E4")
MONEY = '"$"#,##0.00'

LINES = [
    ("Venue", 1500, "Deposit + balance paid"),
    ("Food & drinks", 1200, None),
    ("Supplies & parts", 900, "Watch this one"),
    ("Printing & signage", 400, None),
    ("Prizes", 500, "Gift cards for winners"),
    ("Transport", 300, "Van rental, if needed"),
]

EXPENSES = [
    (date(2026, 10, 1), "Venue deposit", "Venue", "Ava Brooks", 750.00, "receipt_001.pdf", "Approved", "Kai Patel, Priya Shah"),
    (date(2026, 10, 8), "Arduino starter kits", "Supplies & parts", "Daniel Okafor", 268.00, "receipt_002.jpg", "Approved", "Kai Patel, Priya Shah"),
    (date(2026, 10, 12), "PLA filament", "Supplies & parts", "Maya Chen", 150.00, "receipt_003.jpg", "Approved", "Kai Patel"),
    (date(2026, 10, 15), "Snacks, kickoff meeting", "Food & drinks", "Maya Chen", 145.00, "receipt_004.jpg", "Approved", "Kai Patel"),
    (date(2026, 10, 18), "Team hoodies", "Prizes", "Leo Ramirez", 480.00, "quote_hoodies.pdf", "Rejected", "Kai Patel"),
    (date(2026, 10, 22), "Catering deposit", "Food & drinks", "Ava Brooks", 312.40, "receipt_006.pdf", "Approved", "Kai Patel, Priya Shah"),
    (date(2026, 10, 27), "Build-day lunch", "Food & drinks", "Leo Ramirez", 285.00, "receipt_007.jpg", "Approved", "Kai Patel, Priya Shah"),
    (date(2026, 10, 30), "Venue balance", "Venue", "Ava Brooks", 750.00, "receipt_008.pdf", "Approved", "Kai Patel, Priya Shah"),
    (date(2026, 11, 3), "Banner printing", "Printing & signage", "Priya Shah", 275.00, "receipt_009.pdf", "Approved", "Kai Patel, Ava Brooks"),
    (date(2026, 11, 5), "Pizza for build night", "Food & drinks", "Maya Chen", 240.00, "receipt_010.jpg", "Pending", "Ava Brooks"),
    (date(2026, 11, 6), "Servo motors (6)", "Supplies & parts", "Daniel Okafor", 372.00, "receipt_011.pdf", "Pending", None),
]

MEMBERS = [  # placeholder roles and emails
    ("Kai Patel", "Treasurer", "kai@example.org"),
    ("Priya Shah", "President", "priya@example.org"),
    ("Ava Brooks", "Vice President", "ava@example.org"),
    ("Daniel Okafor", "Member", "daniel@example.org"),
    ("Maya Chen", "Member", "maya@example.org"),
    ("Leo Ramirez", "Member", "leo@example.org"),
]


def build(path: Path) -> None:
    wb = Workbook()
    b = wb.active
    b.title = "Budget"
    b["A1"] = "Spring Showcase 2026 – Event Budget"
    b["A1"].font = Font(bold=True, size=14)
    b["A2"] = "Westview Robotics Club · Treasurer: Kai Patel"
    for col, h in zip("ABCDEFH", ["Line", "Budget", "Approved", "Pending", "% used", "Remaining", "Notes"]):
        b[f"{col}3"] = h
        b[f"{col}3"].font = BOLD
        b[f"{col}3"].fill = HDR
    for i, (line, budget, note) in enumerate(LINES):
        r = 4 + i
        b[f"A{r}"] = line
        b[f"B{r}"] = budget
        b[f"C{r}"] = f'=SUMIFS(Expenses!$E:$E,Expenses!$C:$C,$A{r},Expenses!$G:$G,"Approved")'
        b[f"D{r}"] = f'=SUMIFS(Expenses!$E:$E,Expenses!$C:$C,$A{r},Expenses!$G:$G,"Pending")'
        b[f"E{r}"] = f"=IF(B{r}=0,0,(C{r}+D{r})/B{r})"
        b[f"F{r}"] = f"=B{r}-C{r}-D{r}"
        if note:
            b[f"H{r}"] = note
    b["A10"] = "Total"
    b["A10"].font = BOLD
    for col in "BCDF":
        b[f"{col}10"] = f"=SUM({col}4:{col}9)"
        b[f"{col}10"].font = BOLD
    b["E10"] = "=IF(B10=0,0,(C10+D10)/B10)"
    for r in range(4, 11):
        for col in "BCDF":
            b[f"{col}{r}"].number_format = MONEY
        b[f"E{r}"].number_format = "0%"
    b["A12"] = "Rule: purchases over $200 need 2 signatures (president + treasurer)"
    b["A12"].font = Font(bold=True, color="9C4A00")
    b["A13"] = "Log every expense on the Expenses tab and save the receipt in the shared folder."
    b.column_dimensions["A"].width = 22

    e = wb.create_sheet("Expenses")
    for col, h in zip("ABCDEFGH", ["Date", "Description", "Budget line", "Submitted by", "Amount", "Receipt", "Status", "Approved by"]):
        e[f"{col}1"] = h
        e[f"{col}1"].font = BOLD
        e[f"{col}1"].fill = HDR
    for i, row in enumerate(EXPENSES):
        r = 2 + i
        for col, v in zip("ABCDEFGH", row):
            e[f"{col}{r}"] = v
        e[f"A{r}"].number_format = "mm/dd/yyyy"
        e[f"E{r}"].number_format = MONEY
    dv = DataValidation(type="list", formula1='"Pending,Approved,Rejected"', allow_blank=True)
    e.add_data_validation(dv)
    dv.add("G2:G200")
    lines_dv = DataValidation(type="list", formula1="=Budget!$A$4:$A$9", allow_blank=True)
    e.add_data_validation(lines_dv)
    lines_dv.add("C2:C200")

    m = wb.create_sheet("Members")
    for col, h in zip("ABC", ["Name", "Role", "Email"]):
        m[f"{col}1"] = h
        m[f"{col}1"].font = BOLD
        m[f"{col}1"].fill = HDR
    for i, row in enumerate(MEMBERS):
        for col, v in zip("ABC", row):
            m[f"{col}{2 + i}"] = v

    wb.save(path)


def recalc(path: Path) -> None:
    """Round-trip through LibreOffice so formula cells get cached values."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["soffice", "--headless", "--calc", "--convert-to", "xlsx:Calc MS Excel 2007 XML",
             "--outdir", tmp, str(path)],
            check=True, capture_output=True, timeout=120,
        )
        shutil.move(Path(tmp) / path.name, path)


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / OUT.name
        build(raw)
        recalc(raw)
        shutil.move(raw, OUT)
    print(f"wrote {OUT}")
