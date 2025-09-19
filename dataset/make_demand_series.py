#!/usr/bin/env python3
"""
Build per-store daily demand series for a chosen item_id from dataset/sales.csv.

Outputs:
  dataset/demand/<item_id>/
    - demand_store_<store_id>.csv         (date, quantity)
    - demand_all_stores_wide.csv          (date + one column per store) [optional]
    - manifest.json                       (paths, stores, common date window)

Usage:
  python dataset/make_demand_series.py --item 1b240e56c0ea \
      --sales dataset/sales.csv \
      --outdir dataset/demand

Optional:
  --start 2023-01-01 --end 2024-12-31     (trim to a custom window)
  --make-wide                              (also write the wide CSV)
"""

import argparse
import json
import os
from pathlib import Path
import pandas as pd

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--item", required=True, help="item_id to extract (e.g., 1b240e56c0ea)")
    p.add_argument("--sales", default="dataset/sales.csv", help="Path to sales.csv")
    p.add_argument("--outdir", default="dataset/demand", help="Base output directory")
    p.add_argument("--start", default=None, help="Optional start date (YYYY-MM-DD)")
    p.add_argument("--end", default=None, help="Optional end date (YYYY-MM-DD)")
    p.add_argument("--make-wide", action="store_true", help="Also write combined wide CSV")
    return p.parse_args()

def main():
    args = parse_args()
    item_id = args.item
    sales_path = Path(args.sales)
    out_base = Path(args.outdir)
    out_dir = out_base
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[info] Loading {sales_path} ... (first run may take time)")
    # Expect columns: date, item_id, quantity, store_id (plus others we ignore)
    usecols = ["date", "item_id", "store_id", "quantity"]
    df = pd.read_csv(sales_path, usecols=usecols)
    df["date"] = pd.to_datetime(df["date"])

    # Filter to chosen item
    df_item = df[df["item_id"] == item_id].copy()
    if df_item.empty:
        raise SystemExit(f"[error] No rows for item_id={item_id} in {sales_path}")

    # Identify all stores where this item sells
    stores = sorted(df_item["store_id"].unique().tolist())
    print(f"[info] Found {len(stores)} stores for item {item_id}: {stores}")
    if len(stores) < 4:
        print("[warn] Less than 4 stores have this item; continuing anyway.")

    # Build daily series per store, fill missing dates with 0
    per_store = {}
    min_dates, max_dates = [], []
    for sid in stores:
        g = df_item[df_item["store_id"] == sid]
        daily = g.groupby("date")["quantity"].sum().sort_index()

        # Complete calendar: from first to last observed date for this store
        full_idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
        daily_full = daily.reindex(full_idx, fill_value=0)
        daily_full.index.name = "date"

        per_store[sid] = daily_full
        min_dates.append(daily_full.index.min())
        max_dates.append(daily_full.index.max())

    # Align on intersection of dates across all stores
    global_start = max(min_dates)
    global_end = min(max_dates)

    # Optional manual trim
    if args.start:
        global_start = max(global_start, pd.to_datetime(args.start))
    if args.end:
        global_end = min(global_end, pd.to_datetime(args.end))

    if global_end < global_start:
        raise SystemExit("[error] After alignment/trim, global_end < global_start. Relax trims or check data.")

    print(f"[info] Common window: {global_start.date()} to {global_end.date()}")

    # Slice each store to common window and write CSVs
    manifest = {
        "item_id": item_id,
        "stores": [],
        "window": {"start": str(global_start.date()), "end": str(global_end.date())},
        "files": {}
    }

    wide_df = pd.DataFrame(index=pd.date_range(global_start, global_end, freq="D"))
    wide_df.index.name = "date"

    for sid, series in per_store.items():
        sliced = series.loc[global_start:global_end].astype(int)
        out_csv = out_dir / f"demand_store_{sid}.csv"
        sliced.rename("quantity").to_frame().to_csv(out_csv, index=True)
        manifest["stores"].append(sid)
        manifest["files"][str(sid)] = str(out_csv.as_posix())
        wide_df[f"store_{sid}"] = sliced

    # Optionally write a wide CSV (handy for debugging/plots)
    if args.make_wide:
        wide_out = out_dir / "demand_all_stores_wide.csv"
        wide_df.reset_index().to_csv(wide_out, index=False)
        manifest["files"]["wide"] = str(wide_out.as_posix())

    # Write manifest
    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[ok] Wrote per-store demand CSVs + manifest to {out_dir}")

if __name__ == "__main__":
    main()
