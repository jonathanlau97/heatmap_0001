import streamlit as st
import pandas as pd
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
#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: .6rem .6rem .4rem .6rem !important; max-width: 100% !important; }

/* Pill buttons — compact base */
.stButton > button {
    background: #F3F4F6 !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 20px !important;
    color: #6B7280 !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: .63rem !important;
    font-weight: 600 !important;
    padding: 2px 6px !important;
    height: auto !important;
    min-height: 0 !important;
    line-height: 1.35 !important;
    transition: background .12s, border-color .12s, color .12s !important;
    white-space: nowrap !important;
    letter-spacing: .01em !important;
    box-shadow: none !important;
}
.stButton > button:hover {
    background: #E9F9EE !important;
    border-color: #22C55E !important;
    color: #166534 !important;
}
.stButton > button[kind="primary"] {
    background: #DCFCE7 !important;
    border-color: #22C55E !important;
    color: #166534 !important;
    font-weight: 700 !important;
}

/* Airport pill — amber when active */
.ap-active .stButton > button,
.ap-active .stButton > button[kind="primary"] {
    background: #FEF3C7 !important;
    border-color: #F59E0B !important;
    color: #92400E !important;
    font-weight: 700 !important;
}

/* Metrics */
[data-testid="metric-container"] {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: .45rem .75rem !important;
}
[data-testid="metric-container"] label {
    font-size: .55rem !important;
    font-weight: 700 !important;
    color: #9CA3AF !important;
    text-transform: uppercase;
    letter-spacing: .08em;
}
[data-testid="stMetricValue"] {
    font-size: 1.15rem !important;
    font-weight: 800 !important;
    color: #1A1D23 !important;
}

/* Section labels */
.slbl {
    font-size: .53rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: #B0B7C3;
    margin: .4rem 0 .18rem 0;
    display: block;
}

hr { border-color: #F3F4F6 !important; margin: .4rem 0 !important; }
iframe { border-radius: 12px !important; border: 1px solid #E5E7EB !important; }

/* Legend */
.leg-box {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: .55rem .7rem;
    margin-bottom: .4rem;
}
.leg-title { font-size: .53rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; color: #9CA3AF; margin-bottom: .35rem; }
.leg-bar { height: 5px; border-radius: 3px; background: linear-gradient(to right, #3B82F6, #10B981, #F59E0B, #EF4444); margin-bottom: .2rem; }
.leg-labs { display: flex; justify-content: space-between; font-size: .55rem; color: #9CA3AF; }
.ldot-row { display: flex; align-items: center; gap: 5px; margin-bottom: 3px; }
.ldot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.ldot-lbl { font-size: .63rem; color: #374151; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
GITHUB_CSV_URL = "https://raw.githubusercontent.com/jonathanlau97/heatmap_0001/main/heatmap00001.csv"
H3_RES = 6

DAYS_ORDER   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
DAY_MAP_NUM  = {1:"Monday",2:"Tuesday",3:"Wednesday",4:"Thursday",5:"Friday",6:"Saturday",7:"Sunday"}

FOCUS_STATUSES   = ["CANCELLED_BY_DRIVER","CANCELLED_BY_PASSENGER","NO_DRIVER_AVAILABLE","NO_TAKER"]
STATUS_LABELS     = {"CANCELLED_BY_DRIVER":"Cancelled By Driver","CANCELLED_BY_PASSENGER":"Cancelled By Pax",
                     "NO_DRIVER_AVAILABLE":"No Driver","NO_TAKER":"No Taker"}
STATUS_LABELS_LONG= {"CANCELLED_BY_DRIVER":"Cancelled by Driver","CANCELLED_BY_PASSENGER":"Cancelled by Pax",
                     "NO_DRIVER_AVAILABLE":"No Driver Available","NO_TAKER":"No Taker"}
STATUS_COLORS     = {"CANCELLED_BY_DRIVER":"#EF4444","CANCELLED_BY_PASSENGER":"#F97316",
                     "NO_DRIVER_AVAILABLE":"#F59E0B","NO_TAKER":"#3B82F6"}

LANDMARKS = [
    {"n":"Petronas Twin Towers","lat":3.1579,"lng":101.7116,"icon":"🏙️"},
    {"n":"KL Tower",            "lat":3.1528,"lng":101.7039,"icon":"📡"},
    {"n":"Merdeka Square",      "lat":3.1480,"lng":101.6953,"icon":"🏛️"},
    {"n":"Batu Caves",          "lat":3.2379,"lng":101.6840,"icon":"⛩️"},
    {"n":"Pavilion KL",         "lat":3.1490,"lng":101.7131,"icon":"🛍️"},
    {"n":"Mid Valley Megamall", "lat":3.1179,"lng":101.6767,"icon":"🛒"},
    {"n":"Sunway Pyramid",      "lat":3.0732,"lng":101.6060,"icon":"🎡"},
    {"n":"1 Utama",             "lat":3.1518,"lng":101.6151,"icon":"🏪"},
    {"n":"The Curve",           "lat":3.1561,"lng":101.5988,"icon":"🏬"},
    {"n":"IOI City Mall",       "lat":2.9645,"lng":101.7227,"icon":"🏬"},
    {"n":"Paradigm Mall PJ",    "lat":3.1054,"lng":101.6082,"icon":"🏬"},
    {"n":"Setia City Mall",     "lat":3.1200,"lng":101.4890,"icon":"🏬"},
    {"n":"KL Sentral",          "lat":3.1338,"lng":101.6861,"icon":"🚆"},
    {"n":"Masjid Jamek LRT",    "lat":3.1495,"lng":101.6971,"icon":"🚇"},
    {"n":"KLCC LRT",            "lat":3.1614,"lng":101.7118,"icon":"🚇"},
    {"n":"Bukit Bintang MRT",   "lat":3.1452,"lng":101.7118,"icon":"🚇"},
    {"n":"Kelana Jaya LRT",     "lat":3.1074,"lng":101.5861,"icon":"🚇"},
    {"n":"Subang Jaya KTM",     "lat":3.0500,"lng":101.5800,"icon":"🚆"},
    {"n":"Bandar Tasik Selatan","lat":3.0750,"lng":101.7165,"icon":"🚆"},
    {"n":"KLIA",                "lat":2.7456,"lng":101.7099,"icon":"✈️"},
    {"n":"Hospital KL (HKL)",   "lat":3.1731,"lng":101.7051,"icon":"🏥"},
    {"n":"Sunway Medical",      "lat":3.0695,"lng":101.6055,"icon":"🏥"},
    {"n":"Pantai Hospital KL",  "lat":3.1102,"lng":101.6740,"icon":"🏥"},
    {"n":"Damansara Specialist","lat":3.1461,"lng":101.6261,"icon":"🏥"},
    {"n":"Putrajaya Hospital",  "lat":2.9378,"lng":101.6894,"icon":"🏥"},
    {"n":"Universiti Malaya",   "lat":3.1209,"lng":101.6559,"icon":"🎓"},
    {"n":"UiTM Shah Alam",      "lat":3.0731,"lng":101.5154,"icon":"🎓"},
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
        df = pd.read_csv(os.path.join(os.path.dirname(__file__), "heatmap00001.csv"))

    coords = df["Location"].apply(parse_loc)
    df["lat"] = coords.apply(lambda x: x[0])
    df["lng"] = coords.apply(lambda x: x[1])
    df = df.dropna(subset=["lat","lng"]).copy()

    df["TotalBookings"] = pd.to_numeric(df["TotalBookings"], errors="coerce").fillna(1).astype(int)
    df["bookinghour"]   = pd.to_numeric(df["bookinghour"],   errors="coerce").fillna(0).astype(int)

    dow = df["dayofweek"]
    if pd.api.types.is_numeric_dtype(dow):
        df["dayofweek"] = dow.astype(int).map(DAY_MAP_NUM).fillna("Monday")
    else:
        df["dayofweek"] = dow.astype(str).str.strip().str.capitalize()

    df["item_status"] = df["item_status"].astype(str).str.strip()
    df = df[df["item_status"].isin(FOCUS_STATUSES)].copy()

    # Find Airport_Tag column case-insensitively, preserve original casing ("Yes"/"No")
    tag_col = next((c for c in df.columns if c.lower() == "airport_tag"), None)
    if tag_col:
        df["Airport_Tag"] = df[tag_col].astype(str).str.strip()
    else:
        df["Airport_Tag"] = "No"

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
def build_map(df_f):
    m = folium.Map(
        location=[3.10, 101.65],
        zoom_start=11,
        tiles="CartoDB positron",
        zoom_control=True,
        control_scale=False,
        prefer_canvas=True,
    )

    if len(df_f) > 0:
        agg = df_f.groupby("h3_cell")["TotalBookings"].sum()
        mx  = agg.max() or 1
        for cell, density in agg.items():
            try:
                norm = density / mx
                col  = density_color(norm)
                bnd  = h3.cell_to_boundary(cell)
                ctr  = h3.cell_to_latlng(cell)
                folium.Polygon(
                    locations=[[p[0],p[1]] for p in bnd],
                    color=col, weight=0.6, opacity=0.35,
                    fill=True, fill_color=col,
                    fill_opacity=max(0.08, norm * 0.65),
                    tooltip=folium.Tooltip(
                        f"<div style='font-family:Nunito,sans-serif;padding:3px 7px'>"
                        f"<b style='font-size:15px;color:#1A1D23'>{int(density):,}</b></div>",
                        sticky=True,
                    ),
                ).add_to(m)
                folium.Marker(
                    location=[ctr[0],ctr[1]],
                    icon=folium.DivIcon(
                        html=(f"<div style='font-family:Nunito,sans-serif;font-size:8px;"
                              f"font-weight:700;color:{col};text-shadow:0 0 3px #fff,0 0 3px #fff;"
                              f"text-align:center;width:38px;margin-left:-19px;"
                              f"pointer-events:none'>{int(density):,}</div>"),
                        icon_size=(38,12), icon_anchor=(19,6),
                    ),
                ).add_to(m)
            except Exception:
                pass

    # Landmarks always shown
    for lm in LANDMARKS:
        folium.Marker(
            location=[lm["lat"], lm["lng"]],
            icon=folium.DivIcon(
                html=f"<div style='font-size:15px;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,.18))'>{lm['icon']}</div>",
                icon_size=(22,22), icon_anchor=(11,11),
            ),
            popup=folium.Popup(
                f"<div style='font-family:Nunito,sans-serif;text-align:center;padding:2px 4px'>"
                f"<div style='font-size:15px'>{lm['icon']}</div>"
                f"<div style='font-weight:700;font-size:11px;margin-top:1px'>{lm['n']}</div></div>",
                max_width=140,
            ),
            tooltip=lm["n"],
        ).add_to(m)

    return m

# ── SESSION STATE ─────────────────────────────────────────────────────────────
def ss(k, v):
    if k not in st.session_state: st.session_state[k] = v

ss("sel_statuses",   set())
ss("sel_days",       set())
ss("sel_hours",      set())
ss("airport_filter", "All")   # "All" | "Yes" | "No"
ss("clicked_cell",   None)

# ── LOAD ──────────────────────────────────────────────────────────────────────
try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Could not load data.\n\n{e}")
    st.stop()

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='margin:-.6rem -.6rem .55rem -.6rem;padding:.5rem .8rem .45rem;
            background:#fff;border-bottom:1px solid #E5E7EB;display:flex;align-items:baseline;gap:.6rem'>
  <span style='font-size:.9rem;font-weight:800;color:#1A1D23'>🗺️ AirAsia Rides</span>
  <span style='font-size:.6rem;color:#9CA3AF;font-weight:500'>Supply gap heatmap · Klang Valley · 2026 YTD · On-demand only</span>
</div>
""", unsafe_allow_html=True)

# ── FILTERS ───────────────────────────────────────────────────────────────────

# STATUS
st.markdown('<span class="slbl">Status</span>', unsafe_allow_html=True)
s_cols = st.columns(len(FOCUS_STATUSES))
for col, s in zip(s_cols, FOCUS_STATUSES):
    is_on = s in st.session_state.sel_statuses
    if col.button(("✓ " if is_on else "") + STATUS_LABELS[s], key=f"s_{s}",
                  use_container_width=True, type="primary" if is_on else "secondary"):
        st.session_state.sel_statuses.discard(s) if is_on else st.session_state.sel_statuses.add(s)
        st.session_state.clicked_cell = None
        st.rerun()

# DAY — 2-letter abbreviations to keep pills tight
st.markdown('<span class="slbl">Day</span>', unsafe_allow_html=True)
d_cols = st.columns(7)
for col, day in zip(d_cols, DAYS_ORDER):
    is_on = day in st.session_state.sel_days
    if col.button(("✓" if is_on else "") + day[:2], key=f"d_{day}",
                  use_container_width=True, type="primary" if is_on else "secondary"):
        st.session_state.sel_days.discard(day) if is_on else st.session_state.sel_days.add(day)
        st.session_state.clicked_cell = None
        st.rerun()

# HOUR
st.markdown('<span class="slbl">Hour</span>', unsafe_allow_html=True)
for row_hours in [range(0,8), range(8,16), range(16,24)]:
    cols = st.columns(8)
    for col, h in zip(cols, row_hours):
        is_on = h in st.session_state.sel_hours
        if col.button(f"{'✓' if is_on else ''}{h:02d}", key=f"h_{h}",
                      use_container_width=True, type="primary" if is_on else "secondary"):
            st.session_state.sel_hours.discard(h) if is_on else st.session_state.sel_hours.add(h)
            st.session_state.clicked_cell = None
            st.rerun()

# AIRPORT — single pill, 3-way cycle: All → Yes (airport only) → No (non-airport) → All
st.markdown('<span class="slbl">Airport</span>', unsafe_allow_html=True)
_cycle = {"All": ("✈ All", "Yes"), "Yes": ("✈ Only", "No"), "No": ("Non-✈", "All")}
cur_af             = st.session_state.airport_filter
ap_label, next_af  = _cycle[cur_af]
ap_active          = cur_af != "All"

ap_col = st.columns(8)[0]
if ap_active:
    ap_col.markdown("<div class='ap-active'>", unsafe_allow_html=True)
if ap_col.button(ap_label, key="tog_airport", use_container_width=True,
                 type="primary" if ap_active else "secondary"):
    st.session_state.airport_filter = next_af
    st.session_state.clicked_cell   = None
    st.rerun()
if ap_active:
    ap_col.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── FILTER DATA ───────────────────────────────────────────────────────────────
sel_s = st.session_state.sel_statuses or set(FOCUS_STATUSES)
sel_d = st.session_state.sel_days     or set(DAYS_ORDER)
sel_h = st.session_state.sel_hours    or set(range(24))
af    = st.session_state.airport_filter

filtered = df_raw[
    df_raw["item_status"].isin(sel_s) &
    df_raw["dayofweek"].isin(sel_d)   &
    df_raw["bookinghour"].isin(sel_h)
].reset_index(drop=True)

# "Yes" = airport trips only, "No" = non-airport trips only
if af != "All":
    filtered = filtered[filtered["Airport_Tag"] == af].reset_index(drop=True)

# ── METRICS ───────────────────────────────────────────────────────────────────
total_bk = int(filtered["TotalBookings"].sum())
top_s    = filtered.groupby("item_status")["TotalBookings"].sum().idxmax() if len(filtered) else "—"

mc1, mc2, mc3 = st.columns(3)
mc1.metric("Total Bookings", f"{total_bk:,}")
mc2.metric("Top Gap", STATUS_LABELS_LONG.get(top_s, top_s))
mc3.metric("Airport", {"All":"All trips","Yes":"✈ Airport only","No":"Non-airport"}[af])

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ── MAP + LEGEND ──────────────────────────────────────────────────────────────
map_col, leg_col = st.columns([4, 1])

with leg_col:
    st.markdown("""
    <div class='leg-box'>
      <div class='leg-title'>Density</div>
      <div class='leg-bar'></div>
      <div class='leg-labs'><span>Low</span><span>Peak</span></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='leg-box'><div class='leg-title'>Status</div>", unsafe_allow_html=True)
    for s in FOCUS_STATUSES:
        if s not in sel_s: continue
        st.markdown(
            f"<div class='ldot-row'><span class='ldot' style='background:{STATUS_COLORS[s]}'></span>"
            f"<span class='ldot-lbl'>{STATUS_LABELS[s]}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if af != "All":
        chip_col = "#F59E0B" if af == "Yes" else "#6B7280"
        chip_txt = "✈ Airport only" if af == "Yes" else "Non-airport"
        st.markdown(
            f"<div class='leg-box' style='border-color:{chip_col};padding:.4rem .6rem'>"
            f"<div style='font-size:.6rem;font-weight:700;color:{chip_col}'>{chip_txt}</div></div>",
            unsafe_allow_html=True,
        )

with map_col:
    if len(filtered) == 0:
        st.info("No data for the current filters.")
    else:
        with st.spinner("Rendering…"):
            fmap = build_map(filtered)
        map_data = st_folium(fmap, height=455, use_container_width=True,
                             returned_objects=["last_object_clicked"])

        clicked = map_data.get("last_object_clicked")
        if clicked and isinstance(clicked, dict):
            clat, clng = clicked.get("lat"), clicked.get("lng")
            if clat and clng:
                cell = h3.latlng_to_cell(clat, clng, H3_RES)
                st.session_state.clicked_cell = cell if cell in filtered["h3_cell"].values else None

# ── BREAKDOWN TABLE ───────────────────────────────────────────────────────────
st.markdown("<div style='height:3px'></div>", unsafe_allow_html=True)

if st.session_state.clicked_cell:
    cell_df = filtered[filtered["h3_cell"] == st.session_state.clicked_cell]
    cell_bk = int(cell_df["TotalBookings"].sum())
    c1, c2  = st.columns([4,1])
    c1.markdown(
        f"<div style='font-size:.72rem;color:#6B7280;padding:.25rem 0'>"
        f"📍 Selected hex · <b style='color:#1A1D23'>{cell_bk:,} bookings</b></div>",
        unsafe_allow_html=True,
    )
    if c2.button("✕ Clear", key="clear_cell", use_container_width=True):
        st.session_state.clicked_cell = None
        st.rerun()
    table_df = cell_df
else:
    st.markdown("<div style='font-size:.7rem;font-weight:700;color:#1A1D23;margin-bottom:.25rem'>Breakdown by status</div>",
                unsafe_allow_html=True)
    table_df = filtered

if len(table_df) > 0:
    bk = (
        table_df.groupby("item_status")
        .agg(total=("TotalBookings","sum"), locs=("lat","count"))
        .reset_index()
        .sort_values("total", ascending=False)
    )
    bk["share"]       = (bk["total"] / bk["total"].sum() * 100).round(1)
    bk["item_status"] = bk["item_status"].map(STATUS_LABELS_LONG).fillna(bk["item_status"])
    bk.columns        = ["Status","Bookings","Locations","Share %"]
    st.dataframe(
        bk, use_container_width=True, hide_index=True,
        column_config={
            "Status":    st.column_config.TextColumn(width="medium"),
            "Bookings":  st.column_config.NumberColumn(format="%d"),
            "Locations": st.column_config.NumberColumn(format="%d"),
            "Share %":   st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
        }
    )
