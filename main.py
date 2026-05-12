import streamlit as st
import pandas as pd
import numpy as np
import re
import json
import folium
from streamlit_folium import st_folium
import h3

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AirAsia Rides — Demand Heatmap",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"],*{font-family:'Nunito',sans-serif!important}
.stApp{background:#F7F8FA}
.block-container{padding:1rem 1rem 1rem 1rem!important;max-width:100%!important}
section[data-testid="stSidebar"]{display:none}

/* Top bar */
.top-bar{background:#fff;border-bottom:1px solid #EAEDF2;padding:.75rem 1rem .6rem;margin:-1rem -1rem .75rem -1rem}
.top-bar h1{font-size:1.1rem!important;font-weight:800!important;color:#1A1D23!important;margin:0;letter-spacing:-.01em}
.top-bar .sub{font-size:.72rem;color:#9CA3AF;font-weight:500;margin-top:1px}

/* Filter row */
.filter-row{display:flex;flex-wrap:wrap;gap:.5rem;align-items:flex-start;margin-bottom:.75rem}
.filter-group{display:flex;flex-direction:column;gap:.3rem}
.filter-label{font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:#9CA3AF;padding-left:2px}
.pills{display:flex;flex-wrap:wrap;gap:.3rem}

/* Pills */
.pill{display:inline-flex;align-items:center;gap:5px;padding:5px 11px;border-radius:20px;
      border:1.5px solid #E5E7EB;background:#fff;cursor:pointer;
      font-size:.72rem;font-weight:600;color:#6B7280;transition:all .15s;white-space:nowrap;
      user-select:none;-webkit-user-select:none}
.pill.active{background:#1A1D23;border-color:#1A1D23;color:#fff}
.pill .dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.pill-hour{padding:4px 10px;font-size:.72rem}

/* Metrics */
[data-testid="metric-container"]{background:#fff;border:1px solid #EAEDF2;border-radius:12px;padding:.85rem 1rem}
[data-testid="metric-container"] label{font-size:.65rem!important;font-weight:700!important;color:#9CA3AF!important;text-transform:uppercase;letter-spacing:.07em}
[data-testid="stMetricValue"]{font-size:1.5rem!important;font-weight:800!important;color:#1A1D23!important}

/* Map container */
.map-wrap{border-radius:14px;overflow:hidden;border:1px solid #EAEDF2}
iframe{border-radius:14px!important;border:none!important}

/* Breakdown table */
[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden;border:1px solid #EAEDF2}
.stDataFrame th{background:#F7F8FA!important;font-size:.72rem!important;font-weight:700!important;text-transform:uppercase!important;letter-spacing:.06em!important;color:#9CA3AF!important}
.stDataFrame td{font-size:.82rem!important;color:#374151!important}

/* Legend */
.legend-wrap{background:#fff;border:1px solid #EAEDF2;border-radius:12px;padding:.8rem 1rem}
.legend-title{font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:#9CA3AF;margin-bottom:.5rem}
.legend-bar{height:8px;border-radius:4px;background:linear-gradient(to right,#3B82F6,#10B981,#F59E0B,#EF4444);margin-bottom:.3rem}
.legend-labs{display:flex;justify-content:space-between;font-size:.62rem;color:#9CA3AF}
.ldot-row{display:flex;align-items:center;gap:6px;margin-bottom:4px}
.ldot{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.ldot-lbl{font-size:.72rem;color:#374151}

/* Status selected indicator */
.sel-info{font-size:.75rem;color:#6B7280;padding:.4rem .6rem;background:#F7F8FA;border-radius:8px;border:1px solid #EAEDF2}

/* Hour slider override */
.stSlider{margin-top:0!important}
.stSlider [data-baseweb="slider"]{margin-top:0!important}
div[data-testid="stSlider"] label{display:none}

/* Mobile responsiveness */
@media(max-width:768px){
  .block-container{padding:.75rem .75rem .75rem .75rem!important}
  [data-testid="stMetricValue"]{font-size:1.2rem!important}
}
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
GITHUB_CSV_URL = "https://raw.githubusercontent.com/jonathanlau97/heatmap_0001/main/heatmap0001.csv"
H3_RES = 6  # district level (~132 cells for KL)

DAY_MAP = {1:"Monday",2:"Tuesday",3:"Wednesday",4:"Thursday",5:"Friday",6:"Saturday",7:"Sunday"}

ALL_STATUSES = [
    "ARRIVED","NO_TAKER","PENDING_ACCEPTANCE","ON_THE_WAY","NO_SHOW",
    "NO_DRIVER_AVAILABLE","FINALIZE_TOTAL_FARE","NO_REFUND",
    "CANCELLED_BY_DRIVER","REFUND_FAILED","CANCELLED_BY_PASSENGER","REFUND_DONE",
]
STATUS_GROUPS = {
    "Completed": ["ARRIVED","FINALIZE_TOTAL_FARE","ON_THE_WAY","REFUND_DONE"],
    "Cancelled":  ["CANCELLED_BY_DRIVER","CANCELLED_BY_PASSENGER","NO_SHOW","NO_REFUND","REFUND_FAILED"],
    "No Supply": ["NO_TAKER","NO_DRIVER_AVAILABLE"],
    "Pending":   ["PENDING_ACCEPTANCE"],
}
STATUS_COLORS = {
    "ARRIVED":"#22C55E","FINALIZE_TOTAL_FARE":"#16A34A","ON_THE_WAY":"#3B82F6",
    "REFUND_DONE":"#06B6D4","PENDING_ACCEPTANCE":"#93C5FD","NO_TAKER":"#F59E0B",
    "NO_DRIVER_AVAILABLE":"#D97706","NO_SHOW":"#EF4444","CANCELLED_BY_PASSENGER":"#F87171",
    "CANCELLED_BY_DRIVER":"#DC2626","REFUND_FAILED":"#9333EA","NO_REFUND":"#A855F7",
}

LANDMARKS = [
    # KLCC & City Centre
    {"n":"Petronas Twin Towers","s":"KLCC","lat":3.1579,"lng":101.7116,"icon":"🏙️","cat":"landmark"},
    {"n":"KL Tower","s":"Bukit Nanas","lat":3.1528,"lng":101.7039,"icon":"📡","cat":"landmark"},
    {"n":"Merdeka Square","s":"City Centre","lat":3.1480,"lng":101.6953,"icon":"🏛️","cat":"landmark"},
    # Malls
    {"n":"Pavilion KL","s":"Bukit Bintang","lat":3.1490,"lng":101.7131,"icon":"🛍️","cat":"mall"},
    {"n":"Mid Valley Megamall","s":"Bangsar South","lat":3.1179,"lng":101.6767,"icon":"🛒","cat":"mall"},
    {"n":"Sunway Pyramid","s":"Subang Jaya","lat":3.0732,"lng":101.6060,"icon":"🎡","cat":"mall"},
    {"n":"1 Utama","s":"Petaling Jaya","lat":3.1518,"lng":101.6151,"icon":"🏪","cat":"mall"},
    {"n":"The Curve","s":"Mutiara Damansara","lat":3.1561,"lng":101.5988,"icon":"🏬","cat":"mall"},
    {"n":"IOI City Mall","s":"Putrajaya","lat":2.9645,"lng":101.7227,"icon":"🏬","cat":"mall"},
    {"n":"Paradigm Mall PJ","s":"Petaling Jaya","lat":3.1054,"lng":101.6082,"icon":"🏬","cat":"mall"},
    {"n":"Empire Shopping Gallery","s":"Subang Jaya","lat":3.0870,"lng":101.5900,"icon":"🏬","cat":"mall"},
    {"n":"Setia City Mall","s":"Shah Alam","lat":3.1200,"lng":101.4890,"icon":"🏬","cat":"mall"},
    # Train Stations
    {"n":"KL Sentral","s":"Transit Hub","lat":3.1338,"lng":101.6861,"icon":"🚆","cat":"transit"},
    {"n":"Masjid Jamek LRT","s":"City Centre","lat":3.1495,"lng":101.6971,"icon":"🚇","cat":"transit"},
    {"n":"KLCC LRT","s":"KLCC","lat":3.1614,"lng":101.7118,"icon":"🚇","cat":"transit"},
    {"n":"Bukit Bintang MRT","s":"Bukit Bintang","lat":3.1452,"lng":101.7118,"icon":"🚇","cat":"transit"},
    {"n":"Kelana Jaya LRT","s":"Kelana Jaya","lat":3.1074,"lng":101.5861,"icon":"🚇","cat":"transit"},
    {"n":"Subang Jaya KTM","s":"Subang Jaya","lat":3.0500,"lng":101.5800,"icon":"🚆","cat":"transit"},
    {"n":"Bandar Tasik Selatan","s":"Cheras","lat":3.0750,"lng":101.7165,"icon":"🚆","cat":"transit"},
    {"n":"Salak Tinggi ERL","s":"KLIA Link","lat":2.8000,"lng":101.7070,"icon":"🚄","cat":"transit"},
    {"n":"KLIA","s":"International Airport","lat":2.7456,"lng":101.7099,"icon":"✈️","cat":"transit"},
    # Hospitals
    {"n":"KLCC Hospital (HKL)","s":"Jln Pahang","lat":3.1731,"lng":101.7051,"icon":"🏥","cat":"hospital"},
    {"n":"Sunway Medical Centre","s":"Subang Jaya","lat":3.0695,"lng":101.6055,"icon":"🏥","cat":"hospital"},
    {"n":"Pantai Hospital KL","s":"Bangsar","lat":3.1102,"lng":101.6740,"icon":"🏥","cat":"hospital"},
    {"n":"Damansara Specialist","s":"Petaling Jaya","lat":3.1461,"lng":101.6261,"icon":"🏥","cat":"hospital"},
    {"n":"Columbia Asia PJ","s":"Petaling Jaya","lat":3.1043,"lng":101.6390,"icon":"🏥","cat":"hospital"},
    {"n":"Putrajaya Hospital","s":"Putrajaya","lat":2.9378,"lng":101.6894,"icon":"🏥","cat":"hospital"},
    # Universities / Education
    {"n":"UM (Universiti Malaya)","s":"Petaling Jaya","lat":3.1209,"lng":101.6559,"icon":"🎓","cat":"edu"},
    {"n":"UiTM Shah Alam","s":"Shah Alam","lat":3.0731,"lng":101.5154,"icon":"🎓","cat":"edu"},
    # Batu Caves
    {"n":"Batu Caves","s":"Gombak","lat":3.2379,"lng":101.6840,"icon":"⛩️","cat":"landmark"},
]

_LOC_RE = re.compile(r'^(\d+\.\d+)(10[01]\.\d+)$')
def parse_location(loc):
    if pd.isna(loc): return None, None
    m = _LOC_RE.match(str(loc).strip())
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)

# ─── DATA LOADING ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading data…", ttl=3600)
def load_data():
    try:
        df = pd.read_csv(GITHUB_CSV_URL)
    except Exception:
        # fallback: load from local path if running with uploaded file nearby
        import os
        local = os.path.join(os.path.dirname(__file__), "heatmap0001.csv")
        df = pd.read_csv(local)

    coords = df["Location"].apply(parse_location)
    df["lat"] = coords.apply(lambda x: x[0])
    df["lng"] = coords.apply(lambda x: x[1])
    df = df.dropna(subset=["lat","lng"]).copy()
    df["TotalBookings"] = pd.to_numeric(df["TotalBookings"], errors="coerce").fillna(1).astype(int)
    df["bookinghour"]   = pd.to_numeric(df["bookinghour"],   errors="coerce").fillna(0).astype(int)

    # Normalise dayofweek: int 1-7 → day name
    dow = df["dayofweek"]
    if pd.api.types.is_numeric_dtype(dow):
        df["dayofweek"] = dow.astype(int).map(DAY_MAP).fillna("Monday")
    else:
        df["dayofweek"] = dow.astype(str).str.strip().str.capitalize()

    df["item_status"] = df["item_status"].astype(str).str.strip()
    # Pre-compute H3 cell
    df["h3_cell"] = df.apply(lambda r: h3.latlng_to_cell(r["lat"], r["lng"], H3_RES), axis=1)
    return df

# ─── COLOUR SCALE ─────────────────────────────────────────────────────────────
def density_color(norm):
    stops=[(0.,(59,130,246)),(0.33,(16,185,129)),(0.66,(245,158,11)),(1.,(239,68,68))]
    i=0
    while i<len(stops)-2 and norm>stops[i+1][0]: i+=1
    t0,c0=stops[i]; t1,c1=stops[i+1]
    t=(norm-t0)/(t1-t0) if t1!=t0 else 0
    r,g,b=[int(c0[k]+(c1[k]-c0[k])*t) for k in range(3)]
    return f"#{r:02x}{g:02x}{b:02x}"

# ─── MAP BUILDER ──────────────────────────────────────────────────────────────
def build_map(df_filtered, show_landmarks, cat_filters):
    m = folium.Map(
        location=[3.1200, 101.6500],
        zoom_start=11,
        tiles="CartoDB positron",
        control_scale=False,
        zoom_control=True,
    )

    # ── H3 hexagons ──
    if len(df_filtered) > 0:
        agg = df_filtered.groupby("h3_cell")["TotalBookings"].sum()
        mx = agg.max() or 1

        cell_data = {}
        for cell, density in agg.items():
            try:
                bnd = h3.cell_to_boundary(cell)
                norm = density / mx
                col = density_color(norm)
                cell_data[cell] = {"density": int(density), "norm": round(norm, 4), "color": col}
                folium.Polygon(
                    locations=[[p[0], p[1]] for p in bnd],
                    color=col,
                    weight=0.8,
                    opacity=0.5,
                    fill=True,
                    fill_color=col,
                    fill_opacity=max(0.12, norm * 0.72),
                    tooltip=folium.Tooltip(
                        f"<div style='font-family:Nunito,sans-serif;padding:5px 9px'>"
                        f"<span style='font-size:17px;font-weight:800;color:#1A1D23'>"
                        f"{int(density):,}</span><br>"
                        f"<span style='font-size:11px;color:#9CA3AF'>bookings</span>"
                        f"</div>",
                        sticky=True,
                    ),
                ).add_to(m)
            except Exception:
                pass

    # ── Landmarks ──
    if show_landmarks:
        visible_cats = cat_filters if cat_filters else ["landmark","mall","transit","hospital","edu"]
        for lm in LANDMARKS:
            if lm["cat"] not in visible_cats:
                continue
            folium.Marker(
                location=[lm["lat"], lm["lng"]],
                icon=folium.DivIcon(
                    html=(f"<div style='font-size:18px;line-height:1;"
                          f"filter:drop-shadow(0 1px 3px rgba(0,0,0,.18))'>{lm['icon']}</div>"),
                    icon_size=(26, 26),
                    icon_anchor=(13, 13),
                ),
                popup=folium.Popup(
                    (f"<div style='font-family:Nunito,sans-serif;text-align:center;padding:4px 6px'>"
                     f"<div style='font-size:18px'>{lm['icon']}</div>"
                     f"<div style='font-weight:700;font-size:13px;margin-top:3px;color:#1A1D23'>{lm['n']}</div>"
                     f"<div style='font-size:11px;color:#6B7280'>{lm['s']}</div></div>"),
                    max_width=160,
                ),
                tooltip=lm["n"],
            ).add_to(m)
    return m

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "sel_statuses" not in st.session_state:
    st.session_state.sel_statuses = set(ALL_STATUSES)
if "sel_days" not in st.session_state:
    st.session_state.sel_days = set(DAY_MAP.values())
if "hour_range" not in st.session_state:
    st.session_state.hour_range = (0, 23)
if "show_landmarks" not in st.session_state:
    st.session_state.show_landmarks = True
if "show_hex" not in st.session_state:
    st.session_state.show_hex = True
if "lm_cats" not in st.session_state:
    st.session_state.lm_cats = {"landmark","mall","transit","hospital","edu"}
if "clicked_cell" not in st.session_state:
    st.session_state.clicked_cell = None

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
try:
    df_raw = load_data()
    data_ok = True
except Exception as e:
    st.error(f"Could not load data: {e}\n\nUpdate `GITHUB_CSV_URL` at the top of the script.")
    data_ok = False
    st.stop()

existing_statuses = sorted(df_raw["item_status"].unique().tolist())
existing_days = [d for d in DAY_MAP.values() if d in df_raw["dayofweek"].unique()]

# ─── TOP BAR ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class='top-bar'>
  <h1>🗺️ AirAsia Rides — Demand Heatmap</h1>
  <div class='sub'>Klang Valley · 2026 YTD</div>
</div>
""", unsafe_allow_html=True)

# ─── FILTER ROW (top, pill-shaped) ───────────────────────────────────────────
st.markdown("#### Filters")

# ROW 1: Status groups
st.markdown('<div class="filter-label">Status</div>', unsafe_allow_html=True)
grp_cols = st.columns(len(STATUS_GROUPS))
for col, (grp, members) in zip(grp_cols, STATUS_GROUPS.items()):
    grp_members_present = [s for s in members if s in existing_statuses]
    all_selected = all(s in st.session_state.sel_statuses for s in grp_members_present)
    label = f"{'✓ ' if all_selected else ''}{grp}"
    if col.button(label, key=f"grp_{grp}", use_container_width=True):
        if all_selected:
            for s in grp_members_present:
                st.session_state.sel_statuses.discard(s)
        else:
            for s in grp_members_present:
                st.session_state.sel_statuses.add(s)
        st.rerun()

# Individual status pills via HTML + query params trick — use buttons in columns
with st.expander("Individual status filters", expanded=False):
    n_cols = 4
    s_cols = st.columns(n_cols)
    for i, s in enumerate(existing_statuses):
        col = s_cols[i % n_cols]
        is_on = s in st.session_state.sel_statuses
        dot_col = STATUS_COLORS.get(s, "#9CA3AF")
        label = ("✓ " if is_on else "") + s.replace("_", " ").title()
        if col.button(label, key=f"st_{s}", use_container_width=True):
            if is_on:
                st.session_state.sel_statuses.discard(s)
            else:
                st.session_state.sel_statuses.add(s)
            st.rerun()

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ROW 2: Day of week pills
st.markdown('<div class="filter-label">Day of week</div>', unsafe_allow_html=True)
day_cols = st.columns(7)
days_order = list(DAY_MAP.values())
for col, day in zip(day_cols, days_order):
    if day not in existing_days:
        continue
    is_on = day in st.session_state.sel_days
    label = ("✓ " if is_on else "") + day[:3]
    if col.button(label, key=f"day_{day}", use_container_width=True):
        if is_on:
            st.session_state.sel_days.discard(day)
        else:
            st.session_state.sel_days.add(day)
        st.rerun()

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ROW 3: Hour range
st.markdown('<div class="filter-label">Hour of day</div>', unsafe_allow_html=True)
h_col1, h_col2 = st.columns([4, 1])
with h_col1:
    hour_range = st.slider(
        "Hour", 0, 23,
        value=st.session_state.hour_range,
        key="hour_slider",
        label_visibility="collapsed",
    )
    st.session_state.hour_range = hour_range
with h_col2:
    st.markdown(
        f"<div style='padding-top:.5rem;font-size:.78rem;color:#6B7280;font-weight:600'>"
        f"{hour_range[0]:02d}:00 – {hour_range[1]:02d}:00</div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ROW 4: Map layer toggles
st.markdown('<div class="filter-label">Map layers</div>', unsafe_allow_html=True)
lyr_cols = st.columns(7)
# H3 overlay toggle
is_hex = st.session_state.show_hex
if lyr_cols[0].button(("✓ " if is_hex else "") + "H3 Overlay", key="tog_hex", use_container_width=True):
    st.session_state.show_hex = not is_hex
    st.rerun()
# Landmarks toggle
is_lm = st.session_state.show_landmarks
if lyr_cols[1].button(("✓ " if is_lm else "") + "Landmarks", key="tog_lm", use_container_width=True):
    st.session_state.show_landmarks = not is_lm
    st.rerun()

# Landmark category pills
if st.session_state.show_landmarks:
    cat_map = {"landmark":"🏙️ Landmarks","mall":"🛒 Malls","transit":"🚆 Transit","hospital":"🏥 Hospitals","edu":"🎓 Education"}
    for idx, (cat, label) in enumerate(cat_map.items()):
        col = lyr_cols[idx + 2]
        is_cat = cat in st.session_state.lm_cats
        if col.button(("✓ " if is_cat else "") + label, key=f"cat_{cat}", use_container_width=True):
            if is_cat:
                st.session_state.lm_cats.discard(cat)
            else:
                st.session_state.lm_cats.add(cat)
            st.rerun()

st.divider()

# ─── APPLY FILTERS ────────────────────────────────────────────────────────────
sel_statuses = st.session_state.sel_statuses or set(existing_statuses)
sel_days = st.session_state.sel_days or set(existing_days)

filtered = df_raw[
    df_raw["item_status"].isin(sel_statuses) &
    df_raw["dayofweek"].isin(sel_days) &
    df_raw["bookinghour"].between(hour_range[0], hour_range[1])
].reset_index(drop=True)

# ─── METRICS ──────────────────────────────────────────────────────────────────
total_bk = int(filtered["TotalBookings"].sum())
top_s = (filtered.groupby("item_status")["TotalBookings"].sum().idxmax()
         if len(filtered) > 0 else "—")

mc1, mc2 = st.columns(2)
mc1.metric("Total Bookings", f"{total_bk:,}")
mc2.metric("Top Status", top_s.replace("_"," ").title() if top_s != "—" else "—")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ─── MAP + LEGEND ─────────────────────────────────────────────────────────────
map_col, leg_col = st.columns([4, 1])

with leg_col:
    st.markdown("""
    <div class='legend-wrap'>
      <div class='legend-title'>Density</div>
      <div class='legend-bar'></div>
      <div class='legend-labs'><span>Low</span><span>High</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Status colour legend
    st.markdown("<div class='legend-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='legend-title'>Status</div>", unsafe_allow_html=True)
    for s in sorted(sel_statuses)[:12]:
        col = STATUS_COLORS.get(s, "#9CA3AF")
        lbl = s.replace("_"," ").title()
        st.markdown(
            f"<div class='ldot-row'><span class='ldot' style='background:{col}'></span>"
            f"<span class='ldot-lbl'>{lbl}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

with map_col:
    if len(filtered) == 0:
        st.info("No data matches the current filters.")
    else:
        with st.spinner("Rendering map…"):
            fmap = build_map(
                filtered if st.session_state.show_hex else filtered.iloc[0:0],
                st.session_state.show_landmarks,
                list(st.session_state.lm_cats),
            )
        map_data = st_folium(
            fmap,
            height=500,
            use_container_width=True,
            returned_objects=["last_object_clicked"],
        )

        # Detect hex click → find nearest H3 cell
        clicked = map_data.get("last_object_clicked")
        if clicked and isinstance(clicked, dict):
            clat = clicked.get("lat")
            clng = clicked.get("lng")
            if clat and clng:
                cell = h3.latlng_to_cell(clat, clng, H3_RES)
                if cell in filtered["h3_cell"].values:
                    st.session_state.clicked_cell = cell
                else:
                    st.session_state.clicked_cell = None

# ─── BREAKDOWN TABLE ──────────────────────────────────────────────────────────
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

if st.session_state.clicked_cell:
    cell_bk = filtered[filtered["h3_cell"] == st.session_state.clicked_cell]["TotalBookings"].sum()
    st.markdown(
        f"<div class='sel-info'>📍 Showing breakdown for selected hex "
        f"· <b>{int(cell_bk):,} bookings</b> "
        f"<a href='#' style='color:#6B7280;font-size:.7rem' onclick='return false'>"
        f"— click elsewhere to clear</a></div>",
        unsafe_allow_html=True,
    )
    table_df = filtered[filtered["h3_cell"] == st.session_state.clicked_cell]
else:
    st.markdown("#### Breakdown by status")
    table_df = filtered

if len(table_df) > 0:
    bk = (
        table_df.groupby("item_status")
        .agg(total_bookings=("TotalBookings","sum"), locations=("lat","count"))
        .reset_index()
        .sort_values("total_bookings", ascending=False)
    )
    bk["share_%"] = (bk["total_bookings"] / bk["total_bookings"].sum() * 100).round(1)
    bk.columns = ["Status","Total Bookings","Locations","Share %"]
    st.dataframe(
        bk,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status":         st.column_config.TextColumn(width="medium"),
            "Total Bookings": st.column_config.NumberColumn(format="%d"),
            "Locations":      st.column_config.NumberColumn(format="%d"),
            "Share %":        st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
        }
    )
else:
    st.info("No data for selected area.")
