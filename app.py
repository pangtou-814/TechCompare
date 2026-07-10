"""Streamlit web app for IC process data query & visualization."""
import sqlite3
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DB_PATH = Path(__file__).parent / "ic_data2.db"


@st.cache_resource
def get_conn():
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


@st.cache_data
def query(sql, params=None):
    return pd.read_sql(sql, get_conn(), params=params)


def load_filters():
    """Load distinct values for sidebar filters."""
    procs = query("SELECT DISTINCT process FROM ic_data ORDER BY process")
    devs = query("SELECT DISTINCT device_type FROM ic_data ORDER BY device_type")
    vts = query("SELECT DISTINCT vt_type FROM ic_data ORDER BY vt_type")
    params = query("SELECT DISTINCT param_name FROM ic_data ORDER BY param_name")
    return procs["process"].tolist(), devs["device_type"].tolist(), \
        vts["vt_type"].tolist(), params["param_name"].tolist()


def get_bias_ranges(processes, device_types, vt_types):
    """Get min/max bias values for current filter selection."""
    if not processes or not device_types or not vt_types:
        return {}, {}
    # Build WHERE clause
    clauses = []
    params_list = []
    if processes:
        clauses.append(f"process IN ({','.join(['?']*len(processes))})")
        params_list.extend(processes)
    if device_types:
        clauses.append(f"device_type IN ({','.join(['?']*len(device_types))})")
        params_list.extend(device_types)
    if vt_types:
        clauses.append(f"vt_type IN ({','.join(['?']*len(vt_types))})")
        params_list.extend(vt_types)
    where = " AND ".join(clauses)

    mos_vds = query(
        f"SELECT MIN(vds) as mn, MAX(vds) as mx FROM ic_data "
        f"WHERE {where} AND vds IS NOT NULL", params_list
    )
    mos_vgs = query(
        f"SELECT MIN(vgs) as mn, MAX(vgs) as mx FROM ic_data "
        f"WHERE {where} AND vgs IS NOT NULL", params_list
    )
    inv_vdd = query(
        f"SELECT MIN(vdd) as mn, MAX(vdd) as mx FROM ic_data "
        f"WHERE {where} AND vdd IS NOT NULL", params_list
    )
    return (mos_vds, mos_vgs, inv_vdd)


def plot_param_vs_bias(df, x_col, hue_col, title, x_label, y_label):
    """Generic plot: param value vs bias, colored by hue."""
    fig = px.line(
        df, x=x_col, y="value", color=hue_col,
        markers=True, title=title,
        labels={x_col: x_label, "value": y_label, hue_col: hue_col},
    )
    fig.update_layout(
        hovermode="x unified",
        legend_title_text=hue_col,
        xaxis_title=x_label,
        yaxis_title=y_label,
        font=dict(size=13),
        xaxis=dict(
            title=dict(font=dict(size=15, family="Arial")),
            tickfont=dict(size=13),
            showgrid=True, gridwidth=0.5, gridcolor="#e0e0e0",
        ),
        yaxis=dict(
            title=dict(font=dict(size=15, family="Arial")),
            tickfont=dict(size=13),
            showgrid=True, gridwidth=0.5, gridcolor="#e0e0e0",
        ),
        legend=dict(font=dict(size=12)),
    )
    # If x-axis is categorical (VDS as hue), ensure proper numeric sorting
    if x_col == "vgs":
        fig.update_xaxes(title="VGS (V)")
    elif x_col == "vds":
        fig.update_xaxes(title="VDS (V)")
    elif x_col == "vdd":
        fig.update_xaxes(title="VDD (V)")
    return fig


# ── Parameter unit mapping ──
# Raw data in SI units; scale + label for display
PARAM_UNITS = {
    # Frequency
    "ft":               ("GHz",   1e-9),
    # Capacitance
    "cgg":              ("fF",    1e15),
    "cgs":              ("fF",    1e15),
    "cgd":              ("fF",    1e15),
    "cgg_nmos":         ("fF",    1e15),
    "cgs_nmos":         ("fF",    1e15),
    "cgd_nmos":         ("fF",    1e15),
    "cgg_pmos":         ("fF",    1e15),
    "cgs_pmos":         ("fF",    1e15),
    "cgd_pmos":         ("fF",    1e15),
    # Current
    "ids":              ("mA",    1e3),
    # Transconductance / conductance
    "gm":               ("mS",    1e3),
    "gds":              ("mS",    1e3),
    "gm_nmos":          ("mS",    1e3),
    "gds_nmos":         ("mS",    1e3),
    "gm_pmos":          ("mS",    1e3),
    "gds_pmos":         ("mS",    1e3),
    # Transconductance efficiency
    "gm_id":            ("1/V",   1),
    "gm_id_nmos":       ("1/V",   1),
    "gm_id_pmos":       ("1/V",   1),
    # Voltage (keep V)
    "vth":              ("V",     1),
    "vth_nmos":         ("V",     1),
    "vth_pmos":         ("V",     1),
    "vdsat":            ("V",     1),
    "vdsat_nmos":       ("V",     1),
    "vdsat_pmos":       ("V",     1),
    # Gain (unitless)
    "gain":             ("",   1),
    "gain_nmos":        ("",   1),
    "gain_pmos":        ("",   1),
}


def param_unit(param: str) -> tuple[str, float]:
    """Return (unit_label, scale_factor) for a parameter name."""
    base = param.replace("_nmos", "").replace("_pmos", "")
    if base in PARAM_UNITS:
        return PARAM_UNITS[base]
    # Fallback: auto-detect from value range later
    return ("", 1)


def format_value(v, param=None):
    """Format value with engineering prefix. If param known, use its unit."""
    if v is None or pd.isna(v):
        return "N/A"
    if param:
        unit, scale = param_unit(param)
        if scale != 1:
            return f"{v * scale:.4g} {unit}"
    # Generic fallback
    if abs(v) >= 1e9:
        return f"{v*1e-9:.4g} G"
    if abs(v) >= 1e6:
        return f"{v*1e-6:.4g} M"
    if abs(v) >= 1:
        return f"{v:.4g}"
    if abs(v) >= 1e-3:
        return f"{v*1e3:.4g} m"
    if abs(v) >= 1e-6:
        return f"{v*1e6:.4g} u"
    if abs(v) >= 1e-9:
        return f"{v*1e9:.4g} n"
    if abs(v) >= 1e-12:
        return f"{v*1e12:.4g} p"
    if abs(v) >= 1e-15:
        return f"{v*1e15:.4g} f"
    return f"{v:.4g}"


st.set_page_config(
    page_title="IC Process Data Explorer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔬 IC Process Data Explorer")
st.markdown("Query and visualize transistor/inverter simulation data across process nodes.")

# ── Sidebar filters ──
with st.sidebar:
    st.header("Filters")

    all_procs, all_devs, all_vts, all_params = load_filters()

    selected_procs = st.multiselect("Process Node", all_procs, default=all_procs[:1])
    selected_devs = st.multiselect("Device Type", all_devs, default=all_devs[:2])
    selected_vtas = st.multiselect("VT Type", all_vts, default=all_vts)
    selected_params = st.multiselect(
        "Parameters (multi)", all_params,
        default=["gm", "ft", "gm_id", "vth", "ids", "gain"][:3],
    )

    if not (selected_procs and selected_devs and selected_vtas and selected_params):
        st.warning("Select at least one filter in each category.")
        st.stop()

    # ── Bias range ──
    vds_range, vgs_range, vdd_range = get_bias_ranges(
        selected_procs, selected_devs, selected_vtas
    )

    has_mos = any(d in selected_devs for d in ["nmos", "pmos"])
    has_inv = "inv" in selected_devs

    bias_where = []
    bias_params = []

    def build_where(key_list, range_df, label, param_list):
        mn = range_df["mn"].iloc[0]
        mx = range_df["mx"].iloc[0]
        if pd.notna(mn) and pd.notna(mx):
            if mn == mx:
                st.info(f"{label} = {format_value(mn)} (fixed)")
                param_list.append(f"{key_list}={mn}")
            else:
                # round for slider
                mn_r, mx_r = float(mn), float(mx)
                if mx_r - mn_r < 0.01:
                    step = 0.001
                elif mx_r - mn_r < 0.1:
                    step = 0.01
                else:
                    step = 0.1
                sel = st.slider(
                    f"{label} range", mn_r, mx_r,
                    (mn_r, mx_r), step=step, format="%.3f"
                )
                param_list.append(f"{key_list}>={sel[0]}")
                param_list.append(f"{key_list}<={sel[1]}")
            return True
        return False

    if has_mos:
        st.subheader("MOS Bias")
        bias_ok = build_where("vds", vds_range, "VDS", bias_params)
        if bias_ok:
            build_where("vgs", vgs_range, "VGS", bias_params)
    if has_inv:
        st.subheader("INV Bias")
        build_where("vdd", vdd_range, "VDD", bias_params)

    # ── X-axis selector ──
    st.subheader("Plot Options")
    if has_mos:
        x_options = ["vgs", "vds"]
        if has_inv:
            x_options.append("vdd")
    else:
        x_options = ["vdd"]
    x_axis = st.selectbox("X-axis (bias variable)", x_options, index=0)

    hue_options = ["process", "device_type", "vt_type"]
    if has_mos:
        if x_axis == "vgs":
            hue_options.append("vds")
        else:
            hue_options.append("vgs")
    hue = st.selectbox("Color by (hue)", hue_options, index=0)

    plot_type = st.selectbox("Plot Type", ["Line + Markers", "Markers only"], index=0)
    log_y = st.checkbox("Log Y axis", value=False)


# ── Build query ──
where_clauses = [
    f"process IN ({','.join(['?']*len(selected_procs))})",
    f"device_type IN ({','.join(['?']*len(selected_devs))})",
    f"vt_type IN ({','.join(['?']*len(selected_vtas))})",
    f"param_name IN ({','.join(['?']*len(selected_params))})",
]
query_params = list(selected_procs) + list(selected_devs) + \
    list(selected_vtas) + list(selected_params)

# Add bias filters
for bp in bias_params:
    if ">=" in bp:
        k, v = bp.split(">=")
        where_clauses.append(f"{k} >= ?")
        query_params.append(float(v))
    elif "<=" in bp:
        k, v = bp.split("<=")
        where_clauses.append(f"{k} <= ?")
        query_params.append(float(v))
    elif "=" in bp:
        k, v = bp.split("=")
        where_clauses.append(f"{k} = ?")
        query_params.append(float(v))

where_sql = " AND ".join(where_clauses)

df = query(f"""
    SELECT process, device_type, vt_type, point_no,
           vds, vgs, vdd, param_name, value
    FROM ic_data
    WHERE {where_sql}
    ORDER BY process, device_type, vt_type, vds, vgs, vdd, param_name
""", query_params)

if df.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# Remove rows with null x-axis value
df = df.dropna(subset=[x_axis])

# ── Main display ──
st.header("📊 Results")

# Summary stats
total_rows = len(df)
param_count = df["param_name"].nunique()
st.caption(f"{total_rows} data points · {param_count} parameters · "
           f"{df['process'].nunique()} process nodes · "
           f"{df['device_type'].nunique()} device types")

# ── Plotting ──
tab_plot, tab_table, tab_raw = st.tabs(["📈 Plot", "📋 Pivot Table", "📄 Raw Data"])

with tab_plot:
    # Determine which bias dimensions are fixed (not x-axis) → each curve = 1 combo
    fixed_bias_cols = [b for b in ("vds", "vgs", "vdd") if b != x_axis]
    # line_group = process + device + vt + all fixed bias dims + hue (deduped)
    group_cols = ["process", "device_type", "vt_type"]
    for b in fixed_bias_cols:
        if b not in group_cols:
            group_cols.append(b)
    if hue not in group_cols:
        group_cols.append(hue)

    sort_cols = list(dict.fromkeys(group_cols + [x_axis]))
    df_plot = df.sort_values(sort_cols).copy()

    # Scaled value + unit
    df_plot["value_scaled"] = df_plot.apply(
        lambda r: r["value"] * param_unit(r["param_name"])[1], axis=1
    )
    df_plot["line_group"] = df_plot.apply(
        lambda r: "_".join(str(r[c]) for c in group_cols), axis=1
    )

    # Numeric hue → string for discrete coloring
    if hue in ("vds", "vgs", "vdd"):
        df_plot["hue_label"] = df_plot[hue].apply(
            lambda x: f"{x:.3f} V" if pd.notna(x) else "N/A"
        )
        hue_col = "hue_label"
    else:
        hue_col = hue

    # Build composite color label: when VDS varies and isn't hue, encode it
    has_multi_vds = "vds" in fixed_bias_cols and df_plot["vds"].nunique() > 1
    if has_multi_vds:
        df_plot["_color_label"] = df_plot.apply(
            lambda r: f"{r.get(hue_col, '')} VDS={r['vds']:.3f}V"
                      if pd.notna(r.get("vds")) else str(r.get(hue_col, "")),
            axis=1
        )
    else:
        df_plot["_color_label"] = df_plot[hue_col]

    # Build customdata: [process, device, vt, vds, vgs, vdd, point_no, param]
    df_plot["_cd"] = df_plot.apply(lambda r: [
        r["process"], r["device_type"], r["vt_type"],
        r.get("vds"), r.get("vgs"), r.get("vdd"),
        r["point_no"], r["param_name"],
    ], axis=1)

    # ── Per-param plots ──
    for pi, param in enumerate(selected_params):
        sub = df_plot[df_plot["param_name"] == param]
        if sub.empty:
            continue

        unit_label = param_unit(param)[0]
        y_title = f"{param} ({unit_label})" if unit_label else param

        fig = px.line(
            sub,
            x=x_axis, y="value_scaled",
            color="_color_label",
            line_group="line_group",
            markers=True,
            title=f"{param} vs {x_axis.upper()}",
            labels={
                x_axis: x_axis.upper(),
                "value_scaled": y_title,
                "_color_label": f"{hue}{' + VDS' if has_multi_vds else ''}",
            },
        )
        fig.update_traces(
            customdata=sub["_cd"].tolist(),
            hovertemplate=(
                f"<b>{x_axis.upper()}</b>=%{{x:.3f}}<br>"
                f"<b>{y_title}</b>=%{{y:.4g}}<br>"
                "<b>Process</b>=%{customdata[0]}<br>"
                "<b>Device</b>=%{customdata[1]}<br>"
                "<b>VT</b>=%{customdata[2]}<br>"
                "<b>VDS</b>=%{customdata[3]} V<br>"
                "<b>VGS</b>=%{customdata[4]} V<br>"
                "<b>VDD</b>=%{customdata[5]} V<br>"
                "<extra></extra>"
            ),
            line=dict(width=3) if "Line" in plot_type else dict(width=0),
            marker=dict(size=7, line=dict(width=0.5, color="white")),
            hoverlabel=dict(font_size=13, namelength=-1),
        )
        fig.update_layout(
            height=440,
            hovermode="closest",
            hoverdistance=10,
            spikedistance=0,
            showlegend=True,
            margin=dict(l=60, r=20, t=50, b=60),
            font=dict(size=13),
            title=dict(font=dict(size=16, family="Arial")),
            legend=dict(
                title=dict(text=f"{hue}{' + VDS' if has_multi_vds else ''}", font=dict(size=13)),
                font=dict(size=11),
                itemsizing="constant",
            ),
            xaxis=dict(
                title=dict(
                    text=x_axis.upper() if x_axis in ("vgs", "vds", "vdd") else x_axis,
                    font=dict(size=15, family="Arial"),
                ),
                tickfont=dict(size=13),
                showgrid=True, gridwidth=0.5, gridcolor="#e0e0e0",
            ),
            yaxis=dict(
                title=dict(text=y_title, font=dict(size=15, family="Arial")),
                tickfont=dict(size=13),
                showgrid=True, gridwidth=0.5, gridcolor="#e0e0e0",
            ),
        )
        # No spike/vertical line
        fig.update_xaxes(showspikes=False)
        fig.update_yaxes(showspikes=False)
        if log_y:
            fig.update_yaxis(type="log", dtick=1)

        # ── Click handling ──
        ch_key = f"plot_{param}"
        evt = st.plotly_chart(fig, use_container_width=True, key=ch_key, on_select="rerun")

        if evt and evt.get("selection") and evt["selection"].get("points"):
            pts = evt["selection"]["points"]
            if pts:
                cd = pts[0].get("customdata", [])
                if len(cd) >= 7:
                    st.session_state._clicked = {
                        "process": cd[0],
                        "device_type": cd[1],
                        "vt_type": cd[2],
                        "vds": cd[3],
                        "vgs": cd[4],
                        "vdd": cd[5],
                        "point_no": cd[6],
                    }

    # ── Detail panel for clicked point ──
    if "_clicked" in st.session_state and st.session_state._clicked:
        c = st.session_state._clicked
        st.markdown("---")
        st.subheader(f"🔍 Detail @ {c['process']} {c['device_type']} {c['vt_type']} — "
                     f"VDS={c['vds']}V VGS={c['vgs']}V VDD={c['vdd']}V")

        detail_where = ["1=1"]
        detail_params = []
        if c["process"]:
            detail_where.append("process = ?"); detail_params.append(c["process"])
        if c["device_type"]:
            detail_where.append("device_type = ?"); detail_params.append(c["device_type"])
        if c["vt_type"]:
            detail_where.append("vt_type = ?"); detail_params.append(c["vt_type"])
        for col, val in [("vds", c["vds"]), ("vgs", c["vgs"]), ("vdd", c["vdd"])]:
            if val is not None and not (isinstance(val, float) and pd.isna(val)):
                detail_where.append(f"{col} = ?"); detail_params.append(val)
        detail_where.append("point_no = ?"); detail_params.append(c["point_no"])

        detail_df = query(f"""
            SELECT param_name, value FROM ic_data
            WHERE {" AND ".join(detail_where)}
            ORDER BY param_name
        """, detail_params)

        if not detail_df.empty:
            detail_df["unit"] = detail_df["param_name"].apply(lambda p: param_unit(p)[0])
            detail_df["scaled"] = detail_df.apply(
                lambda r: r["value"] * param_unit(r["param_name"])[1], axis=1
            )
            detail_df["display"] = detail_df.apply(
                lambda r: f"{r['scaled']:.4g} {r['unit']}".strip(),
                axis=1
            )
            detail_df.rename(columns={"param_name": "Parameter", "display": "Value"}, inplace=True)
            st.dataframe(
                detail_df[["Parameter", "Value"]],
                use_container_width=True, height=min(40 + len(detail_df) * 36, 500),
                hide_index=True,
                column_config={
                    "Parameter": st.column_config.TextColumn("Parameter", width="medium"),
                    "Value": st.column_config.TextColumn("Value", width="medium"),
                },
            )
        else:
            st.info("No detail data found for this point.")

with tab_table:
    # Pivot table: rows = bias condition, cols = params
    pivot_cols = ["process", "device_type", "vt_type", "point_no", "vds", "vgs", "vdd"]
    available_pivots = [c for c in pivot_cols if df[c].notna().any()]

    # Scale values by their unit factor
    df_pivot = df.copy()
    df_pivot["value_scaled"] = df_pivot.apply(
        lambda r: r["value"] * param_unit(r["param_name"])[1], axis=1
    )

    pivot = df_pivot.pivot_table(
        index=available_pivots,
        columns="param_name",
        values="value_scaled",
        aggfunc="first",
    ).reset_index()

    # Rename bias columns with units
    col_rename = {"vds": "VDS (V)", "vgs": "VGS (V)", "vdd": "VDD (V)"}
    pivot.rename(columns=col_rename, inplace=True)

    # Format numeric values with 4g precision
    for c in pivot.columns:
        if c not in col_rename.values() and c != "point_no" and pivot[c].dtype.kind in ("i", "f"):
            pivot[c] = pivot[c].apply(lambda x: f"{x:.4g}" if pd.notna(x) else "")

    st.dataframe(pivot, use_container_width=True, height=500)

    # Download
    csv = pivot.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download CSV", csv, "ic_data_export.csv", "text/csv"
    )

with tab_raw:
    st.dataframe(df, use_container_width=True, height=500)

    csv_raw = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Raw CSV", csv_raw, "ic_data_raw.csv", "text/csv"
    )

# ── Footer: connection info ──
with st.expander("🔗 Share / Access Info"):
    st.markdown("""
    **Local access:** `http://localhost:8501`

    **LAN access:** Run with `--server.address 0.0.0.0` and share `http://YOUR_IP:8501`

    **DB file:** `ic_data.db` (SQLite, portable)
    """)
