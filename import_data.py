"""Parse IC process CSV data -> SQLite DB."""
import csv
import sqlite3
import re
import os
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "ic_data.db"
DATA_DIR = Path(__file__).parent

def parse_value(s: str) -> float | None:
    """Parse a numeric string like '11.7e9', '800m', '1.2' to float."""
    if not s or not s.strip():
        return None
    s = s.strip().replace('"', '')
    try:
        # Handle scientific notation
        return float(s)
    except ValueError:
        pass
    # Handle 'm' suffix (milli)
    m = re.match(r'^([\d.eE+-]+)m$', s)
    if m:
        try:
            return float(m.group(1)) * 1e-3
        except ValueError:
            return None
    # Handle 'u' suffix (micro)
    m = re.match(r'^([\d.eE+-]+)u$', s)
    if m:
        try:
            return float(m.group(1)) * 1e-6
        except ValueError:
            return None
    return None


def parse_bias_params(line: str) -> dict:
    """Parse 'Parameters: VDS=500m, VGS=300m' or 'Parameters: VDD=900m'."""
    params = {}
    # Remove the "Parameters:" prefix
    text = line.replace("Parameters:", "").strip().strip('"').strip()
    for pair in text.split(","):
        pair = pair.strip()
        m = re.match(r'(\w+)=([\d.mue]+)', pair)
        if m:
            key = m.group(1).lower()
            val = parse_value(m.group(2))
            if val is not None:
                params[key] = val
    return params


def process_csv(filepath: Path) -> list[dict]:
    """Parse one CSV file into a list of row dicts."""
    process_node = filepath.parent.name  # T12 / T22 / T28
    stem = filepath.stem  # e.g. nmos_svt, inv_ulvt
    parts = stem.split("_")
    if len(parts) == 2:
        device_type, vt_type = parts
    else:
        print(f"  Skipping unrecognized file: {filepath}", file=sys.stderr)
        return []

    rows = []
    current_params = {}
    current_point = None

    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)  # skip header
        if not header:
            return rows

        for row in reader:
            if not row or not row[0].strip():
                continue

            first = row[0].strip()

            # Bias/condition line
            if first.startswith("Parameters:") or first.startswith('"Parameters:'):
                current_params = parse_bias_params(row[0])
                continue

            # Data row: Point, Test, Output, Nominal, Spec, Weight, Pass/Fail
            try:
                point = int(first)
            except ValueError:
                continue

            if len(row) < 4:
                continue

            current_point = point
            param_name = row[2].strip()
            nominal = parse_value(row[3])

            rows.append({
                "process": process_node,
                "device_type": device_type,
                "vt_type": vt_type,
                "point_no": current_point,
                "vds": current_params.get("vds"),
                "vgs": current_params.get("vgs"),
                "vdd": current_params.get("vdd"),
                "param_name": param_name,
                "value": nominal,
            })

    return rows


def build_db():
    """Import all CSVs into SQLite."""
    print("Parsing CSV files...")

    all_rows = []
    for csv_file in sorted(DATA_DIR.glob("*/*.csv")):
        if csv_file.parent.name in (".claude",):
            continue
        print(f"  {csv_file.relative_to(DATA_DIR)}")
        rows = process_csv(csv_file)
        all_rows.extend(rows)

    print(f"\nTotal data rows: {len(all_rows)}")

    # Open DB (existing or new), replace all data
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("DROP TABLE IF EXISTS ic_data")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ic_data (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            process       TEXT NOT NULL,
            device_type   TEXT NOT NULL,   -- nmos, pmos, inv
            vt_type       TEXT NOT NULL,   -- svt, ulvt
            point_no      INTEGER,
            vds           REAL,            -- nmos/pmos bias
            vgs           REAL,            -- nmos/pmos bias
            vdd           REAL,            -- inv bias
            param_name    TEXT NOT NULL,
            value         REAL
        )
    """)

    conn.execute("""
        CREATE INDEX idx_data_lookup ON ic_data(
            process, device_type, vt_type, param_name
        )
    """)

    conn.executemany("""
        INSERT INTO ic_data (process, device_type, vt_type, point_no,
                             vds, vgs, vdd, param_name, value)
        VALUES (:process, :device_type, :vt_type, :point_no,
                :vds, :vgs, :vdd, :param_name, :value)
    """, all_rows)

    conn.commit()

    # Stats
    cur = conn.execute("""
        SELECT process, device_type, vt_type, COUNT(DISTINCT param_name), COUNT(*)
        FROM ic_data GROUP BY process, device_type, vt_type
        ORDER BY process, device_type, vt_type
    """)
    print("\n=== DB Summary ===")
    for row in cur.fetchall():
        print(f"  {row[0]}/{row[1]}_{row[2]}: {row[4]} rows, {row[3]} params")

    conn.close()
    print(f"\nDB saved: {DB_PATH} ({DB_PATH.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    build_db()
