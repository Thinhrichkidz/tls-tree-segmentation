import sys, pandas as pd
df = pd.read_csv(sys.argv[1], dtype=str, keep_default_na=False, encoding="utf-8-sig")
print(df.shape)
for c in ["species","log_species","quadrant_id","site_id","live_dead1"]:
    vc = df[c].str.strip().value_counts()
    print("==",c,len(vc)); print(vc.to_string())
