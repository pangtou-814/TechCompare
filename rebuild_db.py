"""Rebuild DB from CSVs (writes to new file to avoid lock)."""
import sqlite3, csv, re
from pathlib import Path

BASE = Path("E:/deskface/tech_compare")
DB = BASE / "ic_data2.db"
PARAM_UNITS = {
    "ft": 1e-9, "cgg": 1e15, "cgs": 1e15, "cgd": 1e15,
    "cgg_nmos": 1e15, "cgs_nmos": 1e15, "cgd_nmos": 1e15,
    "cgg_pmos": 1e15, "cgs_pmos": 1e15, "cgd_pmos": 1e15,
    "ids": 1e3,
    "gm": 1e3, "gds": 1e3,
    "gm_nmos": 1e3, "gds_nmos": 1e3,
    "gm_pmos": 1e3, "gds_pmos": 1e3,
    "gm_id": 1, "gm_id_nmos": 1, "gm_id_pmos": 1,
    "vth": 1, "vth_nmos": 1, "vth_pmos": 1,
    "vdsat": 1, "vdsat_nmos": 1, "vdsat_pmos": 1,
    "gain": 1, "gain_nmos": 1, "gain_pmos": 1,
}


def parse_value(s):
    if not s or not s.strip():
        return None
    s = s.strip().strip('"')
    try:
        return float(s)
    except ValueError:
        pass
    m = re.match(r'^([\d.eE+-]+)m$', s)
    if m:
        try:
            return float(m.group(1)) * 1e-3
        except ValueError:
            return None
    return None


all_rows = []
for csv_file in sorted(BASE.glob("*/nmos_*.csv")) + sorted(BASE.glob("*/pmos_*.csv")) + sorted(BASE.glob("*/inv_*.csv")):
    process = csv_file.parent.name
    parts = csv_file.stem.split("_")
    if len(parts) != 2:
        continue
    device_type, vt_type = parts
    cur_params = {}
    with open(csv_file, newline="", encoding="utf-8-sig") as f:
        next(f)
        for row in csv.reader(f):
            if not row or not row[0].strip():
                continue
            first = row[0].strip()
            if first.startswith("Parameters:") or first.startswith('"Parameters:'):
                text = first.replace("Parameters:", "").strip().strip('"').strip()
                cur_params = {}
                for pair in text.split(","):
                    m = re.match(r'(\w+)=([\d.mue]+)', pair.strip())
                    if m:
                        val = parse_value(m.group(2))
                        if val is not None:
                            cur_params[m.group(1).lower()] = val
                continue
            try:
                pt = int(first)
            except ValueError:
                continue
            if len(row) < 4:
                continue
            val = parse_value(row[3])
            if val is not None:
                all_rows.append(
                    (
                        process,
                        device_type,
                        vt_type,
                        pt,
                        cur_params.get("vds"),
                        cur_params.get("vgs"),
                        cur_params.get("vdd"),
                        row[2].strip(),
                        val,
                    )
                )

print(f"Total rows: {len(all_rows)}")

conn = sqlite3.connect(str(DB))
conn.execute("DROP TABLE IF EXISTS ic_data")
conn.execute("""CREATE TABLE ic_data (
    process TEXT, device_type TEXT, vt_type TEXT, point_no INT,
    vds REAL, vgs REAL, vdd REAL, param_name TEXT, value REAL)""")
conn.executemany("INSERT INTO ic_data VALUES (?,?,?,?,?,?,?,?,?)", all_rows)
conn.commit()
conn.execute("CREATE INDEX idx_ic ON ic_data(process, device_type, vt_type, param_name)")
conn.commit()

for r in conn.execute("""SELECT process, device_type, vt_type,
    COUNT(DISTINCT param_name), COUNT(*) FROM ic_data
    GROUP BY process, device_type, vt_type ORDER BY process, device_type, vt_type"""):
    print(f"  {r[0]}/{r[1]}_{r[2]}: {r[4]} rows, {r[3]} params")

conn.close()
print(f"DB: {DB} ({DB.stat().st_size/1024:.0f} KB)")
