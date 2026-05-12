import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import folium
from streamlit_folium import st_folium
import h3

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AirAsia Rides — Demand Heatmap",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Nunito',sans-serif!important}
.stApp{background:#F7F8FA}
section[data-testid="stSidebar"]{background:#FFFFFF;border-right:1px solid #EAEDF2}
.block-container{padding-top:1.8rem!important;padding-bottom:1rem!important}
h1{font-size:1.45rem!important;font-weight:700!important;color:#1A1D23!important;letter-spacing:-.02em;font-family:'Nunito',sans-serif!important}
h2{font-size:1.05rem!important;font-weight:600!important;color:#1A1D23!important;font-family:'Nunito',sans-serif!important}
h3{font-size:.82rem!important;font-weight:700!important;color:#9CA3AF!important;text-transform:uppercase;letter-spacing:.08em;font-family:'Nunito',sans-serif!important}
[data-testid="metric-container"]{background:#FFFFFF;border:1px solid #EAEDF2;border-radius:12px;padding:1rem 1.2rem}
[data-testid="metric-container"] label{font-size:.7rem!important;font-weight:700!important;color:#9CA3AF!important;text-transform:uppercase;letter-spacing:.07em;font-family:'Nunito',sans-serif!important}
[data-testid="stMetricValue"]{font-size:1.55rem!important;font-weight:700!important;color:#1A1D23!important;font-family:'Nunito',sans-serif!important}
.stMultiSelect span[data-baseweb="tag"]{background:#F0F4FF!important;color:#3B5BDB!important;border-radius:6px!important;font-size:.75rem!important;font-weight:600!important}
.stSelectbox [data-baseweb="select"] div{border-radius:8px!important;border-color:#EAEDF2!important;font-size:.85rem!important}
[data-testid="stFileUploader"]{border:1.5px dashed #D1D5DB;border-radius:12px;padding:.5rem;background:#FAFBFC}
hr{border-color:#EAEDF2!important;margin:1rem 0!important}
.stButton button{background:#1A1D23!important;color:#FFF!important;border:none!important;border-radius:8px!important;font-weight:600!important;font-size:.85rem!important;padding:.55rem 1.2rem!important;width:100%!important;letter-spacing:.02em;font-family:'Nunito',sans-serif!important}
.stButton button:hover{opacity:.82!important}
iframe{border-radius:14px!important;border:1px solid #EAEDF2!important}
.slbl{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:#9CA3AF;margin-bottom:.35rem;margin-top:.1rem;font-family:'Nunito',sans-serif}
.dot-row{display:flex;align-items:center;gap:7px;margin-bottom:5px}
.dot-c{width:10px;height:10px;border-radius:50%;flex-shrink:0;display:inline-block}
.dot-l{font-size:11px;color:#374151;line-height:1.3;font-family:'Nunito',sans-serif}
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
KL_CENTER = [3.1478, 101.6953]

DAY_MAP   = {1:"Monday",2:"Tuesday",3:"Wednesday",4:"Thursday",5:"Friday",6:"Saturday",7:"Sunday"}
DAY_SHORT = {1:"Mon",2:"Tue",3:"Wed",4:"Thu",5:"Fri",6:"Sat",7:"Sun"}

LANDMARKS = [
    {"name":"Petronas Twin Towers","sub":"KLCC",                "lat":3.1579,"lng":101.7116,"icon":"🏙️"},
    {"name":"KL Sentral",          "sub":"Transit Hub",         "lat":3.1338,"lng":101.6861,"icon":"🚆"},
    {"name":"Bukit Bintang",       "sub":"Shopping & Nightlife","lat":3.1466,"lng":101.7099,"icon":"🛍️"},
    {"name":"KLIA",                "sub":"International Airport","lat":2.7456,"lng":101.7099,"icon":"✈️"},
    {"name":"Sunway Pyramid",      "sub":"Subang Jaya",         "lat":3.0732,"lng":101.6060,"icon":"🎡"},
    {"name":"Mid Valley Megamall", "sub":"Bangsar South",       "lat":3.1179,"lng":101.6767,"icon":"🛒"},
    {"name":"Batu Caves",          "sub":"Gombak",              "lat":3.2379,"lng":101.6840,"icon":"⛩️"},
    {"name":"1 Utama",             "sub":"Petaling Jaya",       "lat":3.1518,"lng":101.6151,"icon":"🏪"},
    {"name":"Pavilion KL",         "sub":"Bukit Bintang",       "lat":3.1490,"lng":101.7131,"icon":"🏬"},
]

ALL_STATUSES = [
    "ARRIVED","NO_TAKER","PENDING_ACCEPTANCE","ON_THE_WAY","NO_SHOW",
    "NO_DRIVER_AVAILABLE","FINALIZE_TOTAL_FARE","NO_REFUND",
    "CANCELLED_BY_DRIVER","REFUND_FAILED","CANCELLED_BY_PASSENGER","REFUND_DONE",
]

STATUS_GROUPS = {
    "Completed": ["ARRIVED","FINALIZE_TOTAL_FARE","ON_THE_WAY","REFUND_DONE"],
    "Cancelled": ["CANCELLED_BY_DRIVER","CANCELLED_BY_PASSENGER","NO_SHOW","NO_REFUND","REFUND_FAILED"],
    "No Supply": ["NO_TAKER","NO_DRIVER_AVAILABLE"],
    "Pending":   ["PENDING_ACCEPTANCE"],
}

STATUS_COLORS = {
    "ARRIVED":"#22C55E","FINALIZE_TOTAL_FARE":"#16A34A","ON_THE_WAY":"#3B82F6",
    "REFUND_DONE":"#06B6D4","PENDING_ACCEPTANCE":"#93C5FD",
    "NO_TAKER":"#F59E0B","NO_DRIVER_AVAILABLE":"#D97706","NO_SHOW":"#EF4444",
    "CANCELLED_BY_PASSENGER":"#F87171","CANCELLED_BY_DRIVER":"#DC2626",
    "REFUND_FAILED":"#9333EA","NO_REFUND":"#A855F7",
}

_LOC_RE = re.compile(r'^(\d+\.\d+)(10[01]\.\d+)$')

def parse_location(loc):
    if pd.isna(loc): return None, None
    m = _LOC_RE.match(str(loc).strip())
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)

@st.cache_data(show_spinner="Parsing CSV…")
def load_csv(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes))
    coords = df["Location"].apply(parse_location)
    df["lat"] = coords.apply(lambda x: x[0])
    df["lng"] = coords.apply(lambda x: x[1])
    df = df.dropna(subset=["lat","lng"]).copy()
    df["TotalBookings"] = pd.to_numeric(df["TotalBookings"],errors="coerce").fillna(1).astype(int)
    df["bookinghour"]   = pd.to_numeric(df["bookinghour"],  errors="coerce").fillna(0).astype(int)
    df["dayofweek"]     = pd.to_numeric(df["dayofweek"],    errors="coerce").fillna(1).astype(int)
    df["item_status"]   = df["item_status"].astype(str).str.strip()
    return df

@st.cache_data
def get_sample():
    np.random.seed(42)
    spots = [(3.1579,101.7116,1.0),(3.1338,101.6861,0.9),(3.1490,101.7131,0.85),
             (3.1179,101.6767,0.75),(3.0732,101.6060,0.65),(2.7456,101.7099,0.70)]
    rows = []
    for _ in range(1500):
        la,ln,w = spots[np.random.randint(len(spots))]
        sp = 0.022*(1-w*0.4)
        rows.append({"item_status":ALL_STATUSES[np.random.randint(len(ALL_STATUSES))],
                     "lat":la+(np.random.rand()-.5)*sp,"lng":ln+(np.random.rand()-.5)*sp,
                     "TotalBookings":max(1,int(w*160*np.random.rand())),
                     "bookinghour":np.random.randint(0,24),"dayofweek":np.random.randint(1,8)})
    return pd.DataFrame(rows)

def density_color(norm):
    stops=[(0.,(59,130,246)),(0.33,(16,185,129)),(0.66,(245,158,11)),(1.,(239,68,68))]
    i=0
    while i<len(stops)-2 and norm>stops[i+1][0]: i+=1
    t0,c0=stops[i]; t1,c1=stops[i+1]
    t=(norm-t0)/(t1-t0) if t1!=t0 else 0
    r,g,b=[int(c0[k]+(c1[k]-c0[k])*t) for k in range(3)]
    return f"#{r:02x}{g:02x}{b:02x}"

def build_map(df, resolution, show_points, show_hexes, show_landmarks):
    m = folium.Map(location=KL_CENTER,zoom_start=11,tiles="CartoDB positron",control_scale=True)

    if show_hexes and len(df)>0:
        d2=df.copy()
        d2["cell"]=d2.apply(lambda r:h3.latlng_to_cell(r["lat"],r["lng"],resolution),axis=1)
        agg=d2.groupby("cell")["TotalBookings"].sum()
        mx=agg.max() or 1
        for cell,density in agg.items():
            try:
                bnd=h3.cell_to_boundary(cell)
                norm=density/mx
                col=density_color(norm)
                folium.Polygon(
                    locations=[[p[0],p[1]] for p in bnd],
                    color=col,weight=0.6,opacity=0.45,
                    fill=True,fill_color=col,fill_opacity=0.15+norm*0.55,
                    tooltip=folium.Tooltip(
                        f"<span style='font-family:Nunito,sans-serif'>"
                        f"<b style='font-size:15px'>{int(density):,}</b><br>"
                        f"<span style='color:#6B7280;font-size:12px'>bookings in hex</span></span>",
                        sticky=True)
                ).add_to(m)
            except: pass

    if show_points and len(df)>0:
        samp=df if len(df)<=8000 else df.sample(8000,random_state=42)
        for _,row in samp.iterrows():
            col=STATUS_COLORS.get(row["item_status"],"#9CA3AF")
            rad=max(3,min(11,2+row["TotalBookings"]/40))
            day_lbl=DAY_MAP.get(int(row["dayofweek"]),str(row["dayofweek"]))
            folium.CircleMarker(
                location=[row["lat"],row["lng"]],
                radius=rad,color=col,weight=1.5,
                fill=True,fill_color=col,fill_opacity=0.72,
                tooltip=folium.Tooltip(
                    f"<div style='font-family:Nunito,sans-serif;padding:6px 10px;min-width:170px'>"
                    f"<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
                    f"letter-spacing:.08em;color:#9CA3AF;margin-bottom:4px'>{row['item_status'].replace('_',' ')}</div>"
                    f"<div style='font-size:22px;font-weight:700;color:#1A1D23'>{int(row['TotalBookings']):,}</div>"
                    f"<div style='font-size:12px;color:#6B7280'>total bookings</div>"
                    f"<div style='margin-top:7px;padding-top:6px;border-top:1px solid #EAEDF2;"
                    f"font-size:11px;color:#9CA3AF'>⏰ {int(row['bookinghour']):02d}:00 · {day_lbl}<br>"
                    f"📍 {row['lat']:.5f}, {row['lng']:.5f}</div></div>",sticky=True)
            ).add_to(m)

    if show_landmarks:
        for lm in LANDMARKS:
            folium.Marker(
                location=[lm["lat"],lm["lng"]],
                icon=folium.DivIcon(
                    html=f"<div style='font-size:22px;filter:drop-shadow(0 1px 3px rgba(0,0,0,.2))'>{lm['icon']}</div>",
                    icon_size=(30,30),icon_anchor=(15,15)),
                popup=folium.Popup(
                    f"<div style='font-family:Nunito,sans-serif;text-align:center;padding:4px 6px'>"
                    f"<div style='font-size:18px'>{lm['icon']}</div>"
                    f"<div style='font-weight:700;font-size:13px;margin-top:4px'>{lm['name']}</div>"
                    f"<div style='font-size:11px;color:#6B7280'>{lm['sub']}</div></div>",max_width=180),
                tooltip=lm["name"]
            ).add_to(m)
    return m

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗺️ AirAsia Rides")
    st.markdown("**Demand Heatmap** · Klang Valley")
    st.divider()

    st.markdown('<p class="slbl">Data source</p>',unsafe_allow_html=True)
    uploaded=st.file_uploader("CSV",type=["csv"],label_visibility="collapsed",
        help="Columns: item_status, Location (lat+lng concatenated), TotalBookings, bookinghour, dayofweek")
    if uploaded:
        df_raw=load_csv(uploaded.read())
        st.success(f"✓ {len(df_raw):,} rows loaded",icon="✅")
    else:
        df_raw=get_sample()
        st.caption("Using sample data — upload your CSV above")

    st.divider()

    st.markdown('<p class="slbl">Item status</p>',unsafe_allow_html=True)
    mode=st.radio("Filter by",["By group","By status"],horizontal=True,label_visibility="collapsed")
    existing=sorted(df_raw["item_status"].unique().tolist())

    if mode=="By group":
        sel_groups=st.multiselect("Groups",list(STATUS_GROUPS.keys()),
            default=list(STATUS_GROUPS.keys()),label_visibility="collapsed")
        sel_statuses=[s for g in sel_groups for s in STATUS_GROUPS.get(g,[]) if s in existing]
        if not sel_statuses: sel_statuses=existing
    else:
        sel_statuses=st.multiselect("Statuses",existing,default=existing,label_visibility="collapsed")
        if not sel_statuses: sel_statuses=existing

    st.divider()

    st.markdown('<p class="slbl">Hour of day</p>',unsafe_allow_html=True)
    hour_range=st.slider("Hour",0,23,(0,23),label_visibility="collapsed")
    ca,cb=st.columns(2)
    ca.caption(f"From **{hour_range[0]:02d}:00**")
    cb.caption(f"To **{hour_range[1]:02d}:00**")

    st.divider()

    st.markdown('<p class="slbl">Day of week</p>',unsafe_allow_html=True)
    present_days=sorted(df_raw["dayofweek"].unique().tolist())
    dcols=st.columns(len(present_days))
    sel_days=[]
    for col,d in zip(dcols,present_days):
        if col.checkbox(DAY_SHORT.get(d,str(d)),value=True,key=f"d{d}",label_visibility="collapsed"):
            sel_days.append(d)
        col.caption(DAY_SHORT.get(d,str(d)))
    if not sel_days: sel_days=present_days

    st.divider()

    st.markdown('<p class="slbl">Map layers</p>',unsafe_allow_html=True)
    show_hexes    =st.toggle("H3 hex overlay",  value=True)
    show_points   =st.toggle("Booking points",  value=True)
    show_landmarks=st.toggle("Landmarks",       value=True)

    h3_res=8
    if show_hexes:
        h3_res=st.select_slider("Hex resolution",options=[6,7,8,9],value=8,
            format_func=lambda x:{6:"6 · city",7:"7 · district",8:"8 · neighbourhood",9:"9 · block"}[x])

# ─── FILTER & MAIN ────────────────────────────────────────────────────────────
filtered=df_raw[
    df_raw["item_status"].isin(sel_statuses) &
    df_raw["bookinghour"].between(hour_range[0],hour_range[1]) &
    df_raw["dayofweek"].isin(sel_days)
].reset_index(drop=True)

st.markdown("## Demand Heatmap")

total_bk =int(filtered["TotalBookings"].sum())
n_points =len(filtered)
avg_bk   =round(filtered["TotalBookings"].mean(),1) if n_points>0 else 0
top_s    =filtered.groupby("item_status")["TotalBookings"].sum().idxmax() if n_points>0 else "—"

m1,m2,m3,m4=st.columns(4)
m1.metric("Total bookings",      f"{total_bk:,}")
m2.metric("Locations",           f"{n_points:,}")
m3.metric("Avg bookings / point",f"{avg_bk:,.1f}")
m4.metric("Top status",          top_s.replace("_"," ").title() if top_s!="—" else "—")

st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)

map_col,leg_col=st.columns([5,1])

with leg_col:
    st.markdown('<p class="slbl">Density</p>',unsafe_allow_html=True)
    for lbl,col in [("Peak","#EF4444"),("High","#F59E0B"),("Medium","#10B981"),("Low","#3B82F6")]:
        st.markdown(f"<div class='dot-row'><span class='dot-c' style='background:{col}'></span>"
                    f"<span class='dot-l'>{lbl}</span></div>",unsafe_allow_html=True)
    st.markdown('<p class="slbl" style="margin-top:1rem">Status</p>',unsafe_allow_html=True)
    for s in sel_statuses[:10]:
        col=STATUS_COLORS.get(s,"#9CA3AF")
        st.markdown(f"<div class='dot-row'><span class='dot-c' style='background:{col}'></span>"
                    f"<span class='dot-l'>{s.replace('_',' ').title()}</span></div>",unsafe_allow_html=True)
    if len(sel_statuses)>10: st.caption(f"+{len(sel_statuses)-10} more")

with map_col:
    if n_points==0:
        st.info("No data matches the current filters.")
    else:
        with st.spinner("Rendering map…"):
            fmap=build_map(filtered,h3_res,show_points,show_hexes,show_landmarks)
        st_folium(fmap,height=560,use_container_width=True,returned_objects=[])

st.markdown("<div style='height:10px'></div>",unsafe_allow_html=True)
st.markdown("#### Breakdown by status")

if n_points>0:
    bk=(filtered.groupby("item_status")
        .agg(locations=("lat","count"),total_bookings=("TotalBookings","sum"),
             avg_bookings=("TotalBookings","mean"))
        .reset_index().sort_values("total_bookings",ascending=False))
    bk["avg_bookings"]=bk["avg_bookings"].round(1)
    bk["share_%"]=(bk["total_bookings"]/bk["total_bookings"].sum()*100).round(1)
    bk.columns=["Status","Locations","Total Bookings","Avg / Location","Share %"]
    st.dataframe(bk,use_container_width=True,hide_index=True,
        column_config={
            "Status":        st.column_config.TextColumn(width="medium"),
            "Total Bookings":st.column_config.NumberColumn(format="%d"),
            "Share %":       st.column_config.ProgressColumn(min_value=0,max_value=100,format="%.1f%%"),
        })
else:
    st.info("No data to display.")
