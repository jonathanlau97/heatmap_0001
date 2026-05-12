import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import h3
import io
import json

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AirAsia Rides — Demand Heatmap",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── GLOBAL STYLES ────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
  html, body, [class*="css"], .stApp, .stSidebar, .stMarkdown, .stText,
  input, select, textarea, button, label, p, h1, h2, h3, h4, span, div {
    font-family: 'Nunito', sans-serif !important;
  }

  /* App background */
  .stApp { background: #F7F8FA; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #EAEDF2;
  }
  section[data-testid="stSidebar"] .stMarkdown h1,
  section[data-testid="stSidebar"] .stMarkdown h2,
  section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #1A1D23;
  }

  /* Remove default top padding */
  .block-container { padding-top: 1.8rem !important; padding-bottom: 1rem !important; }

  /* Headings */
  h1 { font-size: 1.5rem !important; font-weight: 700 !important; color: #1A1D23 !important; letter-spacing: -0.02em; }
  h2 { font-size: 1.05rem !important; font-weight: 600 !important; color: #1A1D23 !important; }
  h3 { font-size: 0.85rem !important; font-weight: 600 !important; color: #6B7280 !important; text-transform: uppercase; letter-spacing: 0.07em; }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #EAEDF2;
    border-radius: 12px;
    padding: 1rem 1.2rem;
  }
  [data-testid="metric-container"] label {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    color: #9CA3AF !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
  }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #1A1D23 !important;
  }
  [data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
  }

  /* Multiselect pills */
  .stMultiSelect span[data-baseweb="tag"] {
    background: #F0F4FF !important;
    color: #3B5BDB !important;
    border-radius: 6px !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
  }

  /* Slider */
  .stSlider [data-baseweb="slider"] { padding: 0 !important; }

  /* Selectbox */
  .stSelectbox [data-baseweb="select"] div {
    border-radius: 8px !important;
    border-color: #EAEDF2 !important;
    font-size: 0.85rem !important;
  }

  /* File uploader */
  [data-testid="stFileUploader"] {
    border: 1.5px dashed #D1D5DB;
    border-radius: 12px;
    padding: 0.5rem;
    background: #FAFBFC;
  }

  /* Divider */
  hr { border-color: #EAEDF2 !important; margin: 1rem 0 !important; }

  /* Info box */
  .info-card {
    background: #FFFFFF;
    border: 1px solid #EAEDF2;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    font-size: 0.85rem;
    color: #374151;
    line-height: 1.6;
  }
  .info-card strong { color: #1A1D23; font-weight: 600; }

  /* Section label */
  .section-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #9CA3AF;
    margin-bottom: 0.4rem;
    margin-top: 0.1rem;
  }

  /* Status badge table */
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.03em;
  }

  /* Folium map border */
  iframe { border-radius: 14px !important; border: 1px solid #EAEDF2 !important; }

  /* Button */
  .stButton button {
    background: #1A1D23 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.55rem 1.2rem !important;
    width: 100% !important;
    letter-spacing: 0.02em;
    transition: opacity 0.15s;
  }
  .stButton button:hover { opacity: 0.82 !important; }

  /* Sidebar section spacing */
  .sidebar-section { margin-bottom: 1.4rem; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
KL_CENTER = [3.1478, 101.6953]

LANDMARKS = [
    {"name": "Petronas Twin Towers", "sub": "KLCC", "lat": 3.1579, "lng": 101.7116, "icon": "🏙️"},
    {"name": "KL Sentral", "sub": "Transit Hub", "lat": 3.1338, "lng": 101.6861, "icon": "🚆"},
    {"name": "Bukit Bintang", "sub": "Shopping & Nightlife", "lat": 3.1466, "lng": 101.7099, "icon": "🛍️"},
    {"name": "KLIA", "sub": "International Airport", "lat": 2.7456, "lng": 101.7099, "icon": "✈️"},
    {"name": "Sunway Pyramid", "sub": "Subang Jaya", "lat": 3.0732, "lng": 101.6060, "icon": "🎡"},
    {"name": "Mid Valley Megamall", "sub": "Bangsar South", "lat": 3.1179, "lng": 101.6767, "icon": "🛒"},
    {"name": "Batu Caves", "sub": "Gombak", "lat": 3.2379, "lng": 101.6840, "icon": "⛩️"},
    {"name": "1 Utama", "sub": "Petaling Jaya", "lat": 3.1518, "lng": 101.6151, "icon": "🏪"},
    {"name": "Pavilion KL", "sub": "Bukit Bintang", "lat": 3.1490, "lng": 101.7131, "icon": "🏬"},
]

ALL_STATUSES = [
    "ARRIVED", "NO_TAKER", "PENDING_ACCEPTANCE", "ON_THE_WAY", "NO_SHOW",
    "NO_DRIVER_AVAILABLE", "FINALIZE_TOTAL_FARE", "NO_REFUND",
    "CANCELLED_BY_DRIVER", "REFUND_FAILED", "CANCELLED_BY_PASSENGER"
]

STATUS_GROUPS = {
    "Completed": ["ARRIVED", "FINALIZE_TOTAL_FARE", "ON_THE_WAY"],
    "Cancelled": ["CANCELLED_BY_DRIVER", "CANCELLED_BY_PASSENGER", "NO_SHOW", "NO_REFUND", "REFUND_FAILED"],
    "No Supply": ["NO_TAKER", "NO_DRIVER_AVAILABLE"],
    "Pending": ["PENDING_ACCEPTANCE"],
}

STATUS_COLORS = {
    "ARRIVED": "#22C55E",
    "FINALIZE_TOTAL_FARE": "#16A34A",
    "ON_THE_WAY": "#3B82F6",
    "PENDING_ACCEPTANCE": "#93C5FD",
    "NO_TAKER": "#F59E0B",
    "NO_DRIVER_AVAILABLE": "#D97706",
    "NO_SHOW": "#EF4444",
    "CANCELLED_BY_PASSENGER": "#F87171",
    "CANCELLED_BY_DRIVER": "#DC2626",
    "REFUND_FAILED": "#9333EA",
    "NO_REFUND": "#A855F7",
}

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ─── SAMPLE DATA ──────────────────────────────────────────────────────────────
@st.cache_data
def generate_sample_data():
    np.random.seed(42)
    hotspots = [
        {"lat": 3.1579, "lng": 101.7116, "w": 1.0},
        {"lat": 3.1338, "lng": 101.6861, "w": 0.9},
        {"lat": 3.1490, "lng": 101.7131, "w": 0.85},
        {"lat": 3.1179, "lng": 101.6767, "w": 0.75},
        {"lat": 3.0732, "lng": 101.6060, "w": 0.65},
        {"lat": 3.1518, "lng": 101.6151, "w": 0.60},
        {"lat": 2.7456, "lng": 101.7099, "w": 0.70},
        {"lat": 3.2379, "lng": 101.6840, "w": 0.40},
        {"lat": 3.0983, "lng": 101.6478, "w": 0.50},
        {"lat": 3.0688, "lng": 101.5810, "w": 0.45},
    ]
    rows = []
    for _ in range(2000):
        hs = hotspots[np.random.randint(len(hotspots))]
        spread = 0.022 * (1 - hs["w"] * 0.4)
        lat = hs["lat"] + (np.random.rand() - 0.5) * spread
        lng = hs["lng"] + (np.random.rand() - 0.5) * spread
        status = ALL_STATUSES[np.random.randint(len(ALL_STATUSES))]
        bookings = max(1, int(hs["w"] * 180 * np.random.rand()))
        hour = np.random.randint(0, 24)
        day = DAYS[np.random.randint(7)]
        rows.append({
            "item_status": status,
            "Location": f"{lat:.6f},{lng:.6f}",
            "TotalBookings": bookings,
            "bookinghour": hour,
            "dayofweek": day,
        })
    return pd.DataFrame(rows)


def parse_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    # Parse Location column
    loc = df["Location"].str.split(",", expand=True)
    df["lat"] = pd.to_numeric(loc[0].str.strip(), errors="coerce")
    df["lng"] = pd.to_numeric(loc[1].str.strip(), errors="coerce")
    df["TotalBookings"] = pd.to_numeric(df["TotalBookings"], errors="coerce").fillna(1).astype(int)
    df["bookinghour"] = pd.to_numeric(df["bookinghour"], errors="coerce").fillna(0).astype(int)
    df = df.dropna(subset=["lat", "lng", "item_status"])
    return df


def prepare_df(df):
    """Ensure lat/lng columns exist from Location."""
    if "lat" not in df.columns:
        loc = df["Location"].str.split(",", expand=True)
        df = df.copy()
        df["lat"] = pd.to_numeric(loc[0].str.strip(), errors="coerce")
        df["lng"] = pd.to_numeric(loc[1].str.strip(), errors="coerce")
    return df


# ─── H3 DENSITY ───────────────────────────────────────────────────────────────
def compute_h3_cells(df, resolution):
    df = df.copy()
    df["h3_cell"] = df.apply(lambda r: h3.latlng_to_cell(r["lat"], r["lng"], resolution), axis=1)
    cell_agg = df.groupby("h3_cell")["TotalBookings"].sum().reset_index()
    cell_agg.columns = ["h3_cell", "density"]
    return cell_agg


def density_color(norm, alpha=0.7):
    """Blue → teal → orange → red gradient."""
    stops = [
        (0.0,   (59, 130, 246)),
        (0.33,  (16, 185, 129)),
        (0.66,  (245, 158, 11)),
        (1.0,   (239, 68, 68)),
    ]
    i = 0
    while i < len(stops) - 2 and norm > stops[i + 1][0]:
        i += 1
    t0, c0 = stops[i]
    t1, c1 = stops[i + 1]
    t = (norm - t0) / (t1 - t0) if t1 != t0 else 0
    r = int(c0[0] + (c1[0] - c0[0]) * t)
    g = int(c0[1] + (c1[1] - c0[1]) * t)
    b = int(c0[2] + (c1[2] - c0[2]) * t)
    return f"#{r:02x}{g:02x}{b:02x}", alpha


# ─── MAP BUILDER ──────────────────────────────────────────────────────────────
def build_map(df, resolution, show_points, show_hexes, show_landmarks):
    m = folium.Map(
        location=KL_CENTER,
        zoom_start=11,
        tiles="CartoDB positron",
        control_scale=True,
    )

    # ── H3 HEXAGONS ──
    if show_hexes and len(df) > 0:
        cell_agg = compute_h3_cells(df, resolution)
        max_density = cell_agg["density"].max() or 1
        for _, row in cell_agg.iterrows():
            try:
                boundary = h3.cell_to_boundary(row["h3_cell"])
                norm = row["density"] / max_density
                color, alpha = density_color(norm)
                fill_alpha = 0.15 + norm * 0.55
                folium.Polygon(
                    locations=[[pt[0], pt[1]] for pt in boundary],
                    color=color,
                    weight=0.6,
                    opacity=0.5,
                    fill=True,
                    fill_color=color,
                    fill_opacity=fill_alpha,
                    tooltip=folium.Tooltip(
                        f"<div style='font-family:Nunito,sans-serif;padding:4px 8px'>"
                        f"<b style='font-size:15px'>{int(row['density']):,}</b><br>"
                        f"<span style='color:#6B7280;font-size:12px'>bookings in hex (res {resolution})</span>"
                        f"</div>",
                        sticky=True,
                    ),
                ).add_to(m)
            except Exception:
                pass

    # ── SCATTER POINTS ──
    if show_points and len(df) > 0:
        sample = df if len(df) <= 5000 else df.sample(5000, random_state=42)
        for _, row in sample.iterrows():
            color = STATUS_COLORS.get(row["item_status"], "#9CA3AF")
            radius = max(3, min(12, 2 + row["TotalBookings"] / 50))
            tooltip_html = (
                f"<div style='font-family:Nunito,sans-serif;padding:6px 10px;min-width:160px'>"
                f"<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:0.07em;color:#9CA3AF;margin-bottom:4px'>"
                f"{row['item_status'].replace('_',' ')}</div>"
                f"<div style='font-size:20px;font-weight:700;color:#1A1D23'>"
                f"{int(row['TotalBookings']):,}</div>"
                f"<div style='font-size:12px;color:#6B7280;margin-top:2px'>total bookings</div>"
                f"<div style='font-size:11px;color:#9CA3AF;margin-top:6px;border-top:1px solid #EAEDF2;padding-top:5px'>"
                f"⏰ {int(row['bookinghour']):02d}:00 · {row['dayofweek']}<br>"
                f"📍 {row['lat']:.5f}, {row['lng']:.5f}"
                f"</div></div>"
            )
            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=radius,
                color=color,
                weight=1.5,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                tooltip=folium.Tooltip(tooltip_html, sticky=True),
            ).add_to(m)

    # ── LANDMARKS ──
    if show_landmarks:
        for lm in LANDMARKS:
            popup_html = (
                f"<div style='font-family:Nunito,sans-serif;text-align:center;padding:4px 6px'>"
                f"<div style='font-size:20px'>{lm['icon']}</div>"
                f"<div style='font-weight:700;font-size:13px;color:#1A1D23;margin-top:4px'>{lm['name']}</div>"
                f"<div style='font-size:11px;color:#6B7280'>{lm['sub']}</div>"
                f"</div>"
            )
            icon_html = (
                f"<div style='font-size:22px;line-height:1;filter:drop-shadow(0 1px 3px rgba(0,0,0,0.25))'>"
                f"{lm['icon']}</div>"
            )
            folium.Marker(
                location=[lm["lat"], lm["lng"]],
                icon=folium.DivIcon(html=icon_html, icon_size=(30, 30), icon_anchor=(15, 15)),
                popup=folium.Popup(popup_html, max_width=180),
                tooltip=lm["name"],
            ).add_to(m)

    return m


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗺️ AirAsia Rides")
    st.markdown("**Demand Heatmap** — Klang Valley")
    st.divider()

    # FILE UPLOAD
    st.markdown('<div class="section-label">Data source</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Upload CSV",
        type=["csv"],
        help="Columns: item_status, Location (lat,lng), TotalBookings, bookinghour, dayofweek",
        label_visibility="collapsed",
    )
    if uploaded:
        try:
            raw_df = parse_csv(uploaded)
            st.success(f"✓ {len(raw_df):,} rows loaded", icon="✅")
        except Exception as e:
            st.error(f"Parse error: {e}")
            raw_df = prepare_df(generate_sample_data())
    else:
        raw_df = prepare_df(generate_sample_data())
        st.caption("Using sample data — upload your CSV above")

    st.divider()

    # STATUS FILTER
    st.markdown('<div class="section-label">Item status</div>', unsafe_allow_html=True)
    status_mode = st.radio(
        "Filter by",
        ["By group", "By status"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if status_mode == "By group":
        selected_groups = st.multiselect(
            "Status group",
            list(STATUS_GROUPS.keys()),
            default=list(STATUS_GROUPS.keys()),
            label_visibility="collapsed",
        )
        selected_statuses = [s for g in selected_groups for s in STATUS_GROUPS[g]]
    else:
        selected_statuses = st.multiselect(
            "Statuses",
            ALL_STATUSES,
            default=ALL_STATUSES,
            label_visibility="collapsed",
        )

    st.divider()

    # HOUR FILTER
    st.markdown('<div class="section-label">Hour of day</div>', unsafe_allow_html=True)
    hour_range = st.slider("Hour", 0, 23, (0, 23), label_visibility="collapsed")
    cols = st.columns(2)
    cols[0].caption(f"From **{hour_range[0]:02d}:00**")
    cols[1].caption(f"To **{hour_range[1]:02d}:00**")

    st.divider()

    # DAY OF WEEK
    st.markdown('<div class="section-label">Day of week</div>', unsafe_allow_html=True)
    day_cols = st.columns(7)
    selected_days = []
    for i, (col, day, short) in enumerate(zip(day_cols, DAYS, DAY_SHORT)):
        checked = col.checkbox(short, value=True, key=f"day_{i}", label_visibility="collapsed")
        col.caption(short)
        if checked:
            selected_days.append(day)

    st.divider()

    # MAP OPTIONS
    st.markdown('<div class="section-label">Map layers</div>', unsafe_allow_html=True)
    show_hexes = st.toggle("H3 hex overlay", value=True)
    show_points = st.toggle("Booking points", value=True)
    show_landmarks = st.toggle("Landmarks", value=True)

    if show_hexes:
        h3_resolution = st.select_slider(
            "Hex resolution",
            options=[6, 7, 8, 9],
            value=8,
            format_func=lambda x: {6: "6 · city", 7: "7 · district", 8: "8 · neighbourhood", 9: "9 · block"}[x],
        )
    else:
        h3_resolution = 8

    st.divider()
    apply = st.button("↻  Update map", use_container_width=True)


# ─── FILTER DATA ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def filter_data(df_json, statuses, hour_from, hour_to, days):
    df = pd.read_json(io.StringIO(df_json), orient="records")
    mask = (
        df["item_status"].isin(statuses) &
        df["bookinghour"].between(hour_from, hour_to) &
        df["dayofweek"].isin(days)
    )
    return df[mask].reset_index(drop=True)


if not selected_statuses:
    selected_statuses = ALL_STATUSES
if not selected_days:
    selected_days = DAYS

filtered_df = filter_data(
    raw_df.to_json(orient="records"),
    tuple(selected_statuses),
    hour_range[0],
    hour_range[1],
    tuple(selected_days),
)

# ─── MAIN CONTENT ─────────────────────────────────────────────────────────────
header_col, _ = st.columns([3, 1])
with header_col:
    st.markdown("## Demand Heatmap")

# METRICS ROW
total_bookings = int(filtered_df["TotalBookings"].sum())
total_points   = len(filtered_df)
dominant_status = (
    filtered_df.groupby("item_status")["TotalBookings"].sum().idxmax()
    if len(filtered_df) > 0 else "—"
)
avg_bookings = round(filtered_df["TotalBookings"].mean(), 1) if len(filtered_df) > 0 else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total bookings", f"{total_bookings:,}")
m2.metric("Locations", f"{total_points:,}")
m3.metric("Avg bookings / point", f"{avg_bookings:,.1f}")
m4.metric("Top status", dominant_status.replace("_", " ").title() if dominant_status != "—" else "—")

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# MAP + LEGEND SIDE BY SIDE
map_col, legend_col = st.columns([5, 1])

with legend_col:
    st.markdown('<div class="section-label" style="margin-top:0.2rem">Density</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style='display:flex;flex-direction:column;gap:5px;margin-top:4px'>
      <div style='display:flex;align-items:center;gap:8px;font-size:12px;color:#374151'>
        <span style='width:14px;height:14px;border-radius:3px;background:#EF4444;flex-shrink:0;display:inline-block'></span>Peak
      </div>
      <div style='display:flex;align-items:center;gap:8px;font-size:12px;color:#374151'>
        <span style='width:14px;height:14px;border-radius:3px;background:#F59E0B;flex-shrink:0;display:inline-block'></span>High
      </div>
      <div style='display:flex;align-items:center;gap:8px;font-size:12px;color:#374151'>
        <span style='width:14px;height:14px;border-radius:3px;background:#10B981;flex-shrink:0;display:inline-block'></span>Medium
      </div>
      <div style='display:flex;align-items:center;gap:8px;font-size:12px;color:#374151'>
        <span style='width:14px;height:14px;border-radius:3px;background:#3B82F6;flex-shrink:0;display:inline-block'></span>Low
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label" style="margin-top:1.2rem">Status</div>', unsafe_allow_html=True)
    shown = selected_statuses[:8] if len(selected_statuses) > 8 else selected_statuses
    for s in shown:
        color = STATUS_COLORS.get(s, "#9CA3AF")
        label = s.replace("_", " ").title()
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:7px;margin-bottom:5px'>"
            f"<span style='width:10px;height:10px;border-radius:50%;background:{color};"
            f"flex-shrink:0;display:inline-block'></span>"
            f"<span style='font-size:11px;color:#374151;line-height:1.3'>{label}</span></div>",
            unsafe_allow_html=True,
        )
    if len(selected_statuses) > 8:
        st.caption(f"+{len(selected_statuses)-8} more")

with map_col:
    if len(filtered_df) == 0:
        st.info("No data matches the current filters. Adjust the sidebar selections.")
    else:
        with st.spinner("Rendering map…"):
            folium_map = build_map(
                filtered_df,
                resolution=h3_resolution,
                show_points=show_points,
                show_hexes=show_hexes,
                show_landmarks=show_landmarks,
            )
        st_folium(folium_map, height=560, use_container_width=True, returned_objects=[])

# ─── BREAKDOWN TABLE ──────────────────────────────────────────────────────────
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
st.markdown("#### Breakdown by status")

if len(filtered_df) > 0:
    breakdown = (
        filtered_df.groupby("item_status")
        .agg(locations=("lat", "count"), total_bookings=("TotalBookings", "sum"),
             avg_bookings=("TotalBookings", "mean"))
        .reset_index()
        .sort_values("total_bookings", ascending=False)
    )
    breakdown["avg_bookings"] = breakdown["avg_bookings"].round(1)
    breakdown["share_%"] = (breakdown["total_bookings"] / breakdown["total_bookings"].sum() * 100).round(1)
    breakdown = breakdown.rename(columns={
        "item_status": "Status", "locations": "Locations",
        "total_bookings": "Total Bookings", "avg_bookings": "Avg / Location", "share_%": "Share %"
    })
    st.dataframe(
        breakdown,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn(width="medium"),
            "Total Bookings": st.column_config.NumberColumn(format="%d"),
            "Share %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
        }
    )
else:
    st.info("No data to display.")
