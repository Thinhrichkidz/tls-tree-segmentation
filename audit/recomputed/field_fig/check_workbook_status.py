"""Compare workbook status columns with tree_attributes.csv. Usage: python -I this.py xlsx csv"""
import sys, pandas as pd
w = pd.read_excel(sys.argv[1], sheet_name="All Tree Results"); c = pd.read_csv(sys.argv[2])
print(w.shape); print([x for x in w.columns if "status" in str(x).lower()])
for col in [x for x in w.columns if "status" in str(x).lower()]:
    print(col, w[col].fillna("<blank>").value_counts().to_dict())
