import streamlit as st
import pandas as pd
import numpy as np
import re
import folium
from streamlit_folium import st_folium
import h3

st.set_page_config(
    page_title="AirAsia Rides — Demand",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');

*, html, body, [class*="css"] { font-family: 'Nunito', sans-serif !important; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container {
    padding: .75rem .75rem .5rem .75rem !important;
    max-width: 100% !important;
}

/* Remove streamlit button default styles entirely */
.stButton > button {
    background: #F3F4F6 !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 20px !important;
    color: #6B7280 !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: .68rem !important;
    font-weight: 600 !important;
    padding: 3px 10px !important;
    height: auto !important;
    min-height: 0 !important;
    line-height: 1.4 !important;
    transition: all .15s !important;
    white-space: nowrap !important;
    letter-spacing: .01em !important;
    box-shadow: none !important;
}
.stButton > button:hover {
    background: #E9F9EE !important;
    border-color: #22C55E !important;
    color: #166534 !important;
}
.stButton > button[kind="primary"],
.stButton > button.active-pill {
    background: #DCFCE7 !important;
    border-color: #22C55E !important;
    color: #166534 !important;
    font-weight: 700 !important;
}
/* Active state via data attr trick */
.stButton > button[aria-pressed="true"] {
    background: #DCFCE7 !important;
    border-color: #22C55E !important;
    color: #166534 !important;
}

/* Metrics */
[data-testid="metric-container"] {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: .6rem .9rem !important;
}
[data-testid="metric-container"] label {
    font-size: .6rem !important;
    font-weight: 700 !important;
    color: #9CA3AF !important;
    text-transform: uppercase;
    letter-spacing: .08em;
}
[data-testid="stMetricValue"] {
    font-size: 1.3rem !important;
    font-weight: 800 !important;
    color: #1A1D23 !important;
}

/* Section label */
.slbl {
    font-size: .58rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: #9CA3AF;
    margin: .5rem 0 .25rem 0;
    display: block;
}

/* Divider */
hr { border-color: #F3F4F6 !important; margin: .5rem 0 !important; }

/* Map iframe */
iframe { border-radius: 12px !important; border: 1px solid #E5E7EB !important; }

/* Legend box */
.leg-box {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: .65rem .8rem;
    margin-bottom: .5rem;
}
.leg-title { font-size: .58rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; color: #9CA3AF; margin-bottom: .4rem; }
.leg-bar { height: 6px; border-radius: 3px; background: linear-gradient(to right, #3B82F6, #10B981, #F59E0B, #EF4444); margin-bottom: .25rem; }
.leg-labs { display: flex; justify-content: space-between; font-size: .58rem; color: #9CA3AF; }
.ldot-row { display: flex; align-items: center; gap: 5px; margin-bottom: 3px; }
.ldot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; display: inline-block; }
.ldot-lbl { font-size: .68rem; color: #374151; }

/* Mobile */
@media (max-width: 640px) {
    .block-container { padding: .5rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
    .stButton > button { font-size: .62rem !important; padding: 2px 7px !important; }
}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
GITHUB_CSV_URL = "https://raw.githubusercontent.com/jonathanlau97/heatmap_0001/main/heatmap0001.csv"
H3_RES = 6

DAY_MAP = {1:"Monday",2:"Tuesday",3:"Wednesday",4:"Thursday",5:"Friday",6:"Saturday",7:"Sunday"}
DAYS_ORDER = list(DAY_MAP.values())
DAY_SHORT = {v: v[:3] for v in DAY_MAP.values()}

# Only the 3 supply-side failure statuses
FOCUS_STATUSES = ["CANCELLED_BY_DRIVER", "NO_DRIVER_AVAILABLE", "NO_TAKER"]
STATUS_COLORS = {
    "CANCELLED_BY_DRIVER":  "#EF4444",
    "NO_DRIVER_AVAILABLE":  "#F59E0B",
    "NO_TAKER":             "#3B82F6",
}

LANDMARKS = [
    {"n":"Petronas Twin Towers","s":"KLCC",             "lat":3.1579,"lng":101.7116,"icon":"🏙️","cat":"landmark"},
    {"n":"KL Tower",            "s":"Bukit Nanas",      "lat":3.1528,"lng":101.7039,"icon":"📡","cat":"landmark"},
    {"n":"Merdeka Square",      "s":"City Centre",      "lat":3.1480,"lng":101.6953,"icon":"🏛️","cat":"landmark"},
    {"n":"Batu Caves",          "s":"Gombak",           "lat":3.2379,"lng":101.6840,"icon":"⛩️","cat":"landmark"},
    {"n":"Pavilion KL",         "s":"Bukit Bintang",    "lat":3.1490,"lng":101.7131,"icon":"🛍️","cat":"mall"},
    {"n":"Mid Valley Megamall", "s":"Bangsar South",    "lat":3.1179,"lng":101.6767,"icon":"🛒","cat":"mall"},
    {"n":"Sunway Pyramid",      "s":"Subang Jaya",      "lat":3.0732,"lng":101.6060,"icon":"🎡","cat":"mall"},
    {"n":"1 Utama",             "s":"Petaling Jaya",    "lat":3.1518,"lng":101.6151,"icon":"🏪","cat":"mall"},
    {"n":"The Curve",           "s":"Mutiara Damansara","lat":3.1561,"lng":101.5988,"icon":"🏬","cat":"mall"},
    {"n":"IOI City Mall",       "s":"Putrajaya",        "lat":2.9645,"lng":101.7227,"icon":"🏬","cat":"mall"},
    {"n":"Paradigm Mall PJ",    "s":"Petaling Jaya",    "lat":3.1054,"lng":101.6082,"icon":"🏬","cat":"mall"},
    {"n":"Setia City Mall",     "s":"Shah Alam",        "lat":3.1200,"lng":101.4890,"icon":"🏬","cat":"mall"},
    {"n":"KL Sentral",          "s":"Transit Hub",      "lat":3.1338,"lng":101.6861,"icon":"🚆","cat":"transit"},
    {"n":"Masjid Jamek LRT",    "s":"City Centre",      "lat":3.1495,"lng":101.6971,"icon":"🚇","cat":"transit"},
    {"n":"KLCC LRT",            "s":"KLCC",             "lat":3.1614,"lng":101.7118,"icon":"🚇","cat":"transit"},
    {"n":"Bukit Bintang MRT",   "s":"Bukit Bintang",    "lat":3.1452,"lng":101.7118,"icon":"🚇","cat":"transit"},
    {"n":"Kelana Jaya LRT",     "s":"Kelana Jaya",      "lat":3.1074,"lng":101.5861,"icon":"🚇","cat":"transit"},
    {"n":"Subang Jaya KTM",     "s":"Subang Jaya",      "lat":3.0500,"lng":101.5800,"icon":"🚆","cat":"transit"},
    {"n":"Bandar Tasik Selatan","s":"Cheras",            "lat":3.0750,"lng":101.7165,"icon":"🚆","cat":"transit"},
    {"n":"KLIA",                "s":"Int'l Airport",    "lat":2.7456,"lng":101.7099,"icon":"✈️","cat":"transit"},
    {"n":"Hospital KL (HKL)",   "s":"Jln Pahang",       "lat":3.1731,"lng":101.7051,"icon":"🏥","cat":"hospital"},
    {"n":"Sunway Medical",      "s":"Subang Jaya",      "lat":3.0695,"lng":101.6055,"icon":"🏥","cat":"hospital"},
    {"n":"Pantai Hospital KL",  "s":"Bangsar",          "lat":3.1102,"lng":101.6740,"icon":"🏥","cat":"hospital"},
    {"n":"Damansara Specialist","s":"Petaling Jaya",    "lat":3.1461,"lng":101.6261,"icon":"🏥","cat":"hospital"},
    {"n":"Putrajaya Hospital",  "s":"Putrajaya",        "lat":2.9378,"lng":101.6894,"icon":"🏥","cat":"hospital"},
    {"n":"Universiti Malaya",   "s":"Petaling Jaya",    "lat":3.1209,"lng":101.6559,"icon":"🎓","cat":"edu"},
    {"n":"UiTM Shah Alam",      "s":"Shah Alam",        "lat":3.0731,"lng":101.5154,"icon":"🎓","cat":"edu"},
]

# ── DATA ──────────────────────────────────────────────────────────────────────
_LOC_RE = re.compile(r'^(\d+\.\d+)(10[01]\.\d+)$')

def parse_loc(loc):
    if pd.isna(loc): return None, None
    m = _LOC_RE.match(str(loc).strip())
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)

@st.cache_data(show_spinner="Loading data…", ttl=3600)
def load_data():
    try:
        df = pd.read_csv(GITHUB_CSV_URL)
    except Exception:
        import os
        local = os.path.join(os.path.dirname(__file__), "heatmap0001.csv")
        df = pd.read_csv(local)

    coords = df["Location"].apply(parse_loc)
    df["lat"] = coords.apply(lambda x: x[0])
    df["lng"] = coords.apply(lambda x: x[1])
    df = df.dropna(subset=["lat","lng"]).copy()
    df["TotalBookings"] = pd.to_numeric(df["TotalBookings"], errors="coerce").fillna(1).astype(int)
    df["bookinghour"]   = pd.to_numeric(df["bookinghour"],   errors="coerce").fillna(0).astype(int)
    dow = df["dayofweek"]
    if pd.api.types.is_numeric_dtype(dow):
        df["dayofweek"] = dow.astype(int).map(DAY_MAP).fillna("Monday")
    else:
        df["dayofweek"] = dow.astype(str).str.strip().str.capitalize()
    df["item_status"] = df["item_status"].astype(str).str.strip()
    # Pre-filter to only our 3 focus statuses
    df = df[df["item_status"].isin(FOCUS_STATUSES)].copy()
    df["h3_cell"] = df.apply(lambda r: h3.latlng_to_cell(r["lat"], r["lng"], H3_RES), axis=1)
    return df

# ── COLOUR SCALE ──────────────────────────────────────────────────────────────
def density_color(norm):
    stops = [(0.,(59,130,246)),(0.33,(16,185,129)),(0.66,(245,158,11)),(1.,(239,68,68))]
    i = 0
    while i < len(stops)-2 and norm > stops[i+1][0]: i += 1
    t0,c0 = stops[i]; t1,c1 = stops[i+1]
    t = (norm-t0)/(t1-t0) if t1 != t0 else 0
    r,g,b = [int(c0[k]+(c1[k]-c0[k])*t) for k in range(3)]
    return f"#{r:02x}{g:02x}{b:02x}"

# ── MAP BUILDER ───────────────────────────────────────────────────────────────
def build_map(df_f, show_landmarks, lm_cats):
    m = folium.Map(
        location=[3.10, 101.65],
        zoom_start=11,
        tiles="CartoDB positron",
        zoom_control=True,
        control_scale=False,
    )

    if len(df_f) > 0:
        agg = df_f.groupby("h3_cell")["TotalBookings"].sum()
        mx = agg.max() or 1
        for cell, density in agg.items():
            try:
                bnd = h3.cell_to_boundary(cell)
                norm = density / mx
                col = density_color(norm)
                center = h3.cell_to_latlng(cell)
                # Hex polygon
                folium.Polygon(
                    locations=[[p[0], p[1]] for p in bnd],
                    color=col, weight=0.7, opacity=0.4,
                    fill=True, fill_color=col,
                    fill_opacity=max(0.10, norm * 0.70),
                    tooltip=folium.Tooltip(
                        f"<div style='font-family:Nunito,sans-serif;padding:4px 8px'>"
                        f"<span style='font-size:16px;font-weight:800;color:#1A1D23'>{int(density):,}</span>"
                        f"</div>",
                        sticky=True,
                    ),
                ).add_to(m)
                # Small number label at hex centre
                folium.Marker(
                    location=[center[0], center[1]],
                    icon=folium.DivIcon(
                        html=(
                            f"<div style='font-family:Nunito,sans-serif;"
                            f"font-size:9px;font-weight:700;color:{col};"
                            f"text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 3px #fff;"
                            f"text-align:center;width:40px;margin-left:-20px;"
                            f"pointer-events:none;line-height:1'>"
                            f"{int(density):,}</div>"
                        ),
                        icon_size=(40, 14),
                        icon_anchor=(20, 7),
                    ),
                ).add_to(m)
            except Exception:
                pass

    if show_landmarks:
        vis = lm_cats if lm_cats else {"landmark","mall","transit","hospital","edu"}
        for lm in LANDMARKS:
            if lm["cat"] not in vis: continue
            folium.Marker(
                location=[lm["lat"], lm["lng"]],
                icon=folium.DivIcon(
                    html=f"<div style='font-size:16px;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,.2))'>{lm['icon']}</div>",
                    icon_size=(24,24), icon_anchor=(12,12),
                ),
                popup=folium.Popup(
                    f"<div style='font-family:Nunito,sans-serif;text-align:center;padding:3px 5px'>"
                    f"<div style='font-size:16px'>{lm['icon']}</div>"
                    f"<div style='font-weight:700;font-size:12px;margin-top:2px'>{lm['n']}</div>"
                    f"<div style='font-size:10px;color:#6B7280'>{lm['s']}</div></div>",
                    max_width=150,
                ),
                tooltip=lm["n"],
            ).add_to(m)
    return m

# ── SESSION STATE ─────────────────────────────────────────────────────────────
def ss(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

ss("sel_statuses", set(FOCUS_STATUSES))
ss("sel_days", set(DAYS_ORDER))
ss("sel_hours", set(range(24)))
ss("show_landmarks", True)
ss("show_hex", True)
ss("lm_cats", {"landmark","mall","transit","hospital","edu"})
ss("clicked_cell", None)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Could not load data. Set GITHUB_CSV_URL or place CSV alongside the script.\n\n{e}")
    st.stop()

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='margin:-0.75rem -0.75rem 0.6rem -0.75rem;padding:.6rem .9rem .5rem;
            background:#fff;border-bottom:1px solid #E5E7EB'>
  <div style='font-size:.95rem;font-weight:800;color:#1A1D23;line-height:1.2'>
    🗺️ AirAsia Rides
  </div>
  <div style='font-size:.62rem;color:#9CA3AF;font-weight:500;margin-top:1px'>
    Supply gap heatmap · Klang Valley · 2026 YTD
  </div>
</div>
""", unsafe_allow_html=True)

# ── FILTERS ───────────────────────────────────────────────────────────────────

# STATUS -----------------------------------------------------------------------
st.markdown('<span class="slbl">Status</span>', unsafe_allow_html=True)
s_cols = st.columns(len(FOCUS_STATUSES))
for col, s in zip(s_cols, FOCUS_STATUSES):
    is_on = s in st.session_state.sel_statuses
    label = s.replace("_"," ").replace("Cancelled By","Cancelled by").replace("No Driver Available","No Driver").replace("No Taker","No Taker")
    # Shorten labels
    short = {"CANCELLED_BY_DRIVER":"Cancelled by Driver","NO_DRIVER_AVAILABLE":"No Driver","NO_TAKER":"No Taker"}[s]
    btn_label = ("✓ " if is_on else "") + short
    if col.button(btn_label, key=f"s_{s}", use_container_width=True, type="primary" if is_on else "secondary"):
        if is_on: st.session_state.sel_statuses.discard(s)
        else:     st.session_state.sel_statuses.add(s)
        st.session_state.clicked_cell = None
        st.rerun()

# DAY OF WEEK ------------------------------------------------------------------
st.markdown('<span class="slbl">Day</span>', unsafe_allow_html=True)
d_cols = st.columns(7)
for col, day in zip(d_cols, DAYS_ORDER):
    is_on = day in st.session_state.sel_days
    short = day[:3]
    if col.button(("✓ " if is_on else "") + short, key=f"d_{day}", use_container_width=True, type="primary" if is_on else "secondary"):
        if is_on: st.session_state.sel_days.discard(day)
        else:     st.session_state.sel_days.add(day)
        st.session_state.clicked_cell = None
        st.rerun()

# HOUR OF DAY ------------------------------------------------------------------
st.markdown('<span class="slbl">Hour</span>', unsafe_allow_html=True)
h_rows = [list(range(0, 8)), list(range(8, 16)), list(range(16, 24))]
for row_hours in h_rows:
    cols = st.columns(8)
    for col, h in zip(cols, row_hours):
        is_on = h in st.session_state.sel_hours
        if col.button(f"{'✓' if is_on else ''}{h:02d}", key=f"h_{h}", use_container_width=True, type="primary" if is_on else "secondary"):
            if is_on: st.session_state.sel_hours.discard(h)
            else:     st.session_state.sel_hours.add(h)
            st.session_state.clicked_cell = None
            st.rerun()

# MAP LAYERS -------------------------------------------------------------------
st.markdown('<span class="slbl">Layers</span>', unsafe_allow_html=True)
lyr_cols = st.columns(7)

is_lm = st.session_state.show_landmarks
if lyr_cols[0].button(("✓ " if is_lm else "") + "Landmarks", key="tog_lm", use_container_width=True, type="primary" if is_lm else "secondary"):
    st.session_state.show_landmarks = not is_lm
    st.rerun()

if st.session_state.show_landmarks:
    cat_map = {"landmark":"Sights","mall":"Malls","transit":"Transit","hospital":"Hospitals","edu":"Uni"}
    for idx, (cat, lbl) in enumerate(cat_map.items()):
        col = lyr_cols[idx+1]
        is_cat = cat in st.session_state.lm_cats
        if col.button(("✓ " if is_cat else "") + lbl, key=f"lc_{cat}", use_container_width=True, type="primary" if is_cat else "secondary"):
            if is_cat: st.session_state.lm_cats.discard(cat)
            else:      st.session_state.lm_cats.add(cat)
            st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ── FILTER DATA ───────────────────────────────────────────────────────────────
sel_s = st.session_state.sel_statuses or set(FOCUS_STATUSES)
sel_d = st.session_state.sel_days or set(DAYS_ORDER)
sel_h = st.session_state.sel_hours if st.session_state.sel_hours else set(range(24))

filtered = df_raw[
    df_raw["item_status"].isin(sel_s) &
    df_raw["dayofweek"].isin(sel_d) &
    df_raw["bookinghour"].isin(sel_h)
].reset_index(drop=True)

# ── METRICS ───────────────────────────────────────────────────────────────────
total_bk = int(filtered["TotalBookings"].sum())
top_s = (filtered.groupby("item_status")["TotalBookings"].sum().idxmax()
         if len(filtered) > 0 else "—")
top_s_label = {"CANCELLED_BY_DRIVER":"Cxl by Driver",
               "NO_DRIVER_AVAILABLE":"No Driver Available",
               "NO_TAKER":"No Taker"}.get(top_s, top_s)

mc1, mc2 = st.columns(2)
mc1.metric("Total Bookings", f"{total_bk:,}")
mc2.metric("Top Gap", top_s_label if top_s != "—" else "—")

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ── MAP + LEGEND ──────────────────────────────────────────────────────────────
map_col, leg_col = st.columns([4, 1])

with leg_col:
    st.markdown("""
    <div class='leg-box'>
      <div class='leg-title'>Density</div>
      <div class='leg-bar'></div>
      <div class='leg-labs'><span>Low</span><span>Peak</span></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='leg-box'>", unsafe_allow_html=True)
    st.markdown("<div class='leg-title'>Status</div>", unsafe_allow_html=True)
    status_labels = {"CANCELLED_BY_DRIVER":"Cxl Driver","NO_DRIVER_AVAILABLE":"No Driver","NO_TAKER":"No Taker"}
    for s in FOCUS_STATUSES:
        if s not in sel_s: continue
        c = STATUS_COLORS[s]
        st.markdown(
            f"<div class='ldot-row'><span class='ldot' style='background:{c}'></span>"
            f"<span class='ldot-lbl'>{status_labels[s]}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

with map_col:
    if len(filtered) == 0:
        st.info("No data for the current filters.")
    else:
        with st.spinner("Rendering…"):
            fmap = build_map(filtered, st.session_state.show_landmarks, st.session_state.lm_cats)
        map_data = st_folium(fmap, height=460, use_container_width=True, returned_objects=["last_object_clicked"])

        clicked = map_data.get("last_object_clicked")
        if clicked and isinstance(clicked, dict):
            clat, clng = clicked.get("lat"), clicked.get("lng")
            if clat and clng:
                cell = h3.latlng_to_cell(clat, clng, H3_RES)
                st.session_state.clicked_cell = cell if cell in filtered["h3_cell"].values else None

# ── BREAKDOWN TABLE ───────────────────────────────────────────────────────────
st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

if st.session_state.clicked_cell:
    cell_df = filtered[filtered["h3_cell"] == st.session_state.clicked_cell]
    cell_bk = int(cell_df["TotalBookings"].sum())
    c1, c2 = st.columns([4,1])
    c1.markdown(
        f"<div style='font-size:.75rem;color:#6B7280;padding:.3rem 0'>"
        f"📍 Selected hex · <b style='color:#1A1D23'>{cell_bk:,} bookings</b></div>",
        unsafe_allow_html=True,
    )
    if c2.button("✕ Clear", key="clear_cell", use_container_width=True):
        st.session_state.clicked_cell = None
        st.rerun()
    table_df = cell_df
else:
    st.markdown("<div style='font-size:.75rem;font-weight:700;color:#1A1D23;margin-bottom:.3rem'>Breakdown by status</div>", unsafe_allow_html=True)
    table_df = filtered

if len(table_df) > 0:
    bk = (
        table_df.groupby("item_status")
        .agg(total=("TotalBookings","sum"), locs=("lat","count"))
        .reset_index()
        .sort_values("total", ascending=False)
    )
    bk["share"] = (bk["total"] / bk["total"].sum() * 100).round(1)
    bk["item_status"] = bk["item_status"].map(status_labels).fillna(bk["item_status"])
    bk.columns = ["Status","Bookings","Locations","Share %"]
    st.dataframe(
        bk, use_container_width=True, hide_index=True,
        column_config={
            "Status":    st.column_config.TextColumn(width="medium"),
            "Bookings":  st.column_config.NumberColumn(format="%d"),
            "Locations": st.column_config.NumberColumn(format="%d"),
            "Share %":   st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
        }
    )
