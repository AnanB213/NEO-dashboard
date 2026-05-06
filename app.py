"""
Near-Earth Object (NEO) Dashboard
CS-122 | Section 03 | Spring 2026
Team: Anan Belsare & Ethan Nepo

A Streamlit dashboard that fetches live data from NASA's NeoWs API
and presents it through graphs and a filterable data table.

Libraries used:
    - streamlit:  web UI framework
    - requests:   HTTP calls to NASA NeoWs API
    - pandas:     data parsing and manipulation
    - plotly:     interactive charts (scatter, bar, pie)
    - datetime:   date-range logic
    - hashlib:    deterministic NEO-of-the-Day selection
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib
from typing import Optional


# Constants
# ─────────
NASA_API_BASE = "https://api.nasa.gov/neo/rest/v1"
DEFAULT_API_KEY = "DEMO_KEY"  # Works out of the box, but better with actual key

# Page configuration, first Streamlit command
st.set_page_config(
    page_title="NEO Dashboard",
    page_icon="☄️",
    layout="wide",
    initial_sidebar_state="expanded",
)



# Data Fetching & Parsing
# ───────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_neo_feed(start_date: str, end_date: str, api_key: str) -> dict:
    """
    Query the NASA NeoWs /feed endpoint for a given date range.

    Parameters
    ----------
    start_date : str   ISO date string (YYYY-MM-DD)
    end_date   : str   ISO date string (YYYY-MM-DD), ≤ 7 days after start
    api_key    : str   NASA API key

    Returns
    -------
    dict : raw JSON response from the API

    The @st.cache_data decorator caches results for 1 hour so repeated
    interactions with the dashboard do not re-hit the API.
    """
    url = f"{NASA_API_BASE}/feed"
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "api_key": api_key,
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def parse_neo_data(raw: dict) -> pd.DataFrame:
    """
    Flatten the nested NeoWs JSON into a tabular DataFrame.

    The API groups NEOs by date, and each NEO contains nested dicts for
    diameter estimates, close-approach details, and velocity.  This
    function extracts the relevant fields into a single flat row per NEO.

    Parameters
    ----------
    raw : dict   The JSON dict returned by fetch_neo_feed()

    Returns
    -------
    pd.DataFrame with one row per NEO close approach
    """
    records = []

    for date_str, neo_list in raw.get("near_earth_objects", {}).items():
        for neo in neo_list:
            # each NEO can have multiple close approaches so we take the first
            close = neo["close_approach_data"][0] if neo["close_approach_data"] else {}

            records.append({
                "id": neo["id"],
                "name": neo["name"],
                "close_approach_date": date_str,
                "abs_magnitude": neo.get("absolute_magnitude_h"),
                # diameter estimates in meters and kilometers
                "est_diameter_min_m": neo["estimated_diameter"]["meters"]["estimated_diameter_min"],
                "est_diameter_max_m": neo["estimated_diameter"]["meters"]["estimated_diameter_max"],
                "est_diameter_min_km": neo["estimated_diameter"]["kilometers"]["estimated_diameter_min"],
                "est_diameter_max_km": neo["estimated_diameter"]["kilometers"]["estimated_diameter_max"],
                # hazard flag from NASA's own classification
                "is_potentially_hazardous": neo.get("is_potentially_hazardous_asteroid", False),
                # approach distance in two units
                "miss_distance_km": float(close.get("miss_distance", {}).get("kilometers", 0)),
                "miss_distance_lunar": float(close.get("miss_distance", {}).get("lunar", 0)),
                # approach velocity in two units
                "relative_velocity_kmh": float(close.get("relative_velocity", {}).get("kilometers_per_hour", 0)),
                "relative_velocity_kms": float(close.get("relative_velocity", {}).get("kilometers_per_second", 0)),
                "orbiting_body": close.get("orbiting_body", ""),
                "nasa_jpl_url": neo.get("nasa_jpl_url", ""),
            })

    df = pd.DataFrame(records)

    if not df.empty:
        df["close_approach_date"] = pd.to_datetime(df["close_approach_date"])
        # compute average of min/max diameter for a single value
        df["est_diameter_avg_m"] = (df["est_diameter_min_m"] + df["est_diameter_max_m"]) / 2
        df.sort_values("close_approach_date", inplace=True)
        df.reset_index(drop=True, inplace=True)

    return df



# NEO of the Day
# ──────────────
def pick_neo_of_the_day(df: pd.DataFrame, date: datetime) -> Optional[pd.Series]:
    """
    Deterministically select one NEO to feature for a given calendar day.

    Uses an MD5 hash of the date string as a seed so the same object is
    highlighted all day, but a different one appears tomorrow.

    Parameters
    ----------
    df   : pd.DataFrame   The full NEO dataset
    date : datetime        The current date

    Returns
    -------
    pd.Series for the selected NEO, or None if the DataFrame is empty
    """
    if df.empty:
        return None
    seed = int(hashlib.md5(date.strftime("%Y-%m-%d").encode()).hexdigest(), 16)
    idx = seed % len(df)
    return df.iloc[idx]


def render_neo_of_the_day(neo: pd.Series):
    """Display a styled fact card with key stats for the featured NEO."""
    hazard_badge = (
        "🔴 Potentially Hazardous" if neo["is_potentially_hazardous"]
        else "🟢 Not Hazardous"
    )

    st.markdown("### ☄️ NEO of the Day")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Name", neo["name"])
        st.caption(f"ID: {neo['id']}")
    with col2:
        st.metric("Avg Diameter", f"{neo['est_diameter_avg_m']:.1f} m")
        st.metric("Abs Magnitude", f"{neo['abs_magnitude']:.2f}")
    with col3:
        st.metric("Miss Distance", f"{neo['miss_distance_lunar']:.2f} LD")
        st.metric("Velocity", f"{neo['relative_velocity_kms']:.2f} km/s")

    st.markdown(f"**Status:** {hazard_badge}")
    st.markdown(
        f"**Close Approach:** {neo['close_approach_date'].strftime('%B %d, %Y')} &nbsp;|&nbsp; "
        f"**Miss Distance:** {neo['miss_distance_km']:,.0f} km &nbsp;|&nbsp; "
        f"**Orbiting Body:** {neo['orbiting_body']}"
    )
    if neo["nasa_jpl_url"]:
        st.markdown(f"[View on NASA JPL →]({neo['nasa_jpl_url']})")



# Visualizations
# ──────────────
def chart_miss_distance_timeline(df: pd.DataFrame):
    """
    Scatter plot: miss distance (lunar distances) over time.

    Each dot represents one NEO close approach.  Dot size encodes
    estimated diameter; color encodes hazard classification.
    """
    st.markdown("### 📏 Miss-Distance Timeline")
    st.caption("Each dot is a NEO close approach. Hover for details.")

    fig = px.scatter(
        df,
        x="close_approach_date",
        y="miss_distance_lunar",
        color="is_potentially_hazardous",
        size="est_diameter_avg_m",
        hover_name="name",
        hover_data={
            "miss_distance_km": ":,.0f",
            "relative_velocity_kms": ":.2f",
            "est_diameter_avg_m": ":.1f",
            "is_potentially_hazardous": True,
            "close_approach_date": False,
            "miss_distance_lunar": ":.2f",
        },
        color_discrete_map={True: "#e74c3c", False: "#2ecc71"},
        labels={
            "close_approach_date": "Close Approach Date",
            "miss_distance_lunar": "Miss Distance (Lunar Distances)",
            "is_potentially_hazardous": "Potentially Hazardous",
            "est_diameter_avg_m": "Avg Diameter (m)",
            "miss_distance_km": "Miss Distance (km)",
            "relative_velocity_kms": "Velocity (km/s)",
        },
    )
    fig.update_layout(
        height=450,
        legend_title_text="Potentially Hazardous",
        xaxis_title="Date",
        yaxis_title="Miss Distance (Lunar Distances)",
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_size_comparison(df: pd.DataFrame):
    """
    Horizontal bar chart of the 15 largest NEOs by average diameter.

    Bars are colored by hazard status so users can quickly see whether
    the biggest objects are also the most dangerous.
    """
    st.markdown("### 📐 Size Comparison — Top 15 Largest NEOs")

    top = df.nlargest(15, "est_diameter_avg_m").copy()
    top.sort_values("est_diameter_avg_m", ascending=True, inplace=True)

    fig = px.bar(
        top,
        x="est_diameter_avg_m",
        y="name",
        orientation="h",
        color="is_potentially_hazardous",
        color_discrete_map={True: "#e74c3c", False: "#2ecc71"},
        hover_data={
            "est_diameter_min_m": ":.1f",
            "est_diameter_max_m": ":.1f",
            "miss_distance_lunar": ":.2f",
        },
        labels={
            "est_diameter_avg_m": "Avg Diameter (m)",
            "name": "",
            "is_potentially_hazardous": "Potentially Hazardous",
            "est_diameter_min_m": "Min Diameter (m)",
            "est_diameter_max_m": "Max Diameter (m)",
            "miss_distance_lunar": "Miss Distance (LD)",
        },
    )
    fig.update_layout(height=500, yaxis_title="", legend_title_text="Potentially Hazardous")
    st.plotly_chart(fig, use_container_width=True)


def chart_hazard_breakdown(df: pd.DataFrame):
    """
    Donut chart and summary metrics splitting NEOs into hazardous
    vs. non-hazardous.  Also highlights the closest hazardous object.
    """
    st.markdown("### ⚠️ Hazard Breakdown")

    counts = df["is_potentially_hazardous"].value_counts()
    hazardous = counts.get(True, 0)
    safe = counts.get(False, 0)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Total NEOs", len(df))
        st.metric("Potentially Hazardous", hazardous)
        st.metric("Not Hazardous", safe)
        # Show the closest hazardous NEO if any exist
        if hazardous > 0:
            closest_hazard = (
                df[df["is_potentially_hazardous"]]
                .nsmallest(1, "miss_distance_km")
                .iloc[0]
            )
            st.markdown("**Closest hazardous NEO:**")
            st.markdown(
                f"{closest_hazard['name']}  \n"
                f"{closest_hazard['miss_distance_km']:,.0f} km  \n"
                f"({closest_hazard['miss_distance_lunar']:.2f} LD)"
            )

    with col2:
        fig = px.pie(
            names=["Not Hazardous", "Potentially Hazardous"],
            values=[safe, hazardous],
            color_discrete_sequence=["#2ecc71", "#e74c3c"],
            hole=0.45,
        )
        fig.update_traces(textinfo="label+percent+value")
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def chart_velocity_vs_size(df: pd.DataFrame):
    """
    Scatter plot correlating estimated diameter with approach velocity.

    Useful for seeing whether larger objects tend to move faster or
    slower, and how hazard status relates to both variables.
    """
    st.markdown("### 🚀 Velocity vs. Size")

    fig = px.scatter(
        df,
        x="est_diameter_avg_m",
        y="relative_velocity_kms",
        color="is_potentially_hazardous",
        hover_name="name",
        size="miss_distance_lunar",
        color_discrete_map={True: "#e74c3c", False: "#2ecc71"},
        labels={
            "est_diameter_avg_m": "Avg Diameter (m)",
            "relative_velocity_kms": "Relative Velocity (km/s)",
            "is_potentially_hazardous": "Potentially Hazardous",
            "miss_distance_lunar": "Miss Distance (LD)",
        },
    )
    fig.update_layout(height=450, legend_title_text="Potentially Hazardous")
    st.plotly_chart(fig, use_container_width=True)



# Data Table with Filters
# ───────────────────────
def render_data_table(df: pd.DataFrame):
    """
    Render a filterable, sortable data table of all NEO records.

    Sidebar-style filters let users narrow results by hazard status,
    minimum diameter, and maximum miss distance.
    """
    st.markdown("### 🗂️ Close-Approach Data Table")

    # Filter controls in three columns
    f1, f2, f3 = st.columns(3)
    with f1:
        hazard_filter = st.selectbox(
            "Hazard Status",
            ["All", "Potentially Hazardous Only", "Non-Hazardous Only"],
        )
    with f2:
        min_diameter = st.number_input(
            "Min Diameter (m)", min_value=0.0, value=0.0, step=10.0
        )
    with f3:
        max_miss = st.number_input(
            "Max Miss Distance (LD)",
            min_value=0.0,
            value=float(df["miss_distance_lunar"].max()) if not df.empty else 100.0,
            step=1.0,
        )

    # Apply filters to a copy of the DataFrame
    filtered = df.copy()
    if hazard_filter == "Potentially Hazardous Only":
        filtered = filtered[filtered["is_potentially_hazardous"]]
    elif hazard_filter == "Non-Hazardous Only":
        filtered = filtered[~filtered["is_potentially_hazardous"]]

    filtered = filtered[filtered["est_diameter_avg_m"] >= min_diameter]
    filtered = filtered[filtered["miss_distance_lunar"] <= max_miss]

    # Select and rename columns for display
    display_cols = [
        "name",
        "close_approach_date",
        "est_diameter_avg_m",
        "miss_distance_km",
        "miss_distance_lunar",
        "relative_velocity_kms",
        "is_potentially_hazardous",
    ]
    renamed = {
        "name": "Name",
        "close_approach_date": "Close Approach",
        "est_diameter_avg_m": "Avg Diameter (m)",
        "miss_distance_km": "Miss Dist (km)",
        "miss_distance_lunar": "Miss Dist (LD)",
        "relative_velocity_kms": "Velocity (km/s)",
        "is_potentially_hazardous": "Hazardous?",
    }

    st.dataframe(
        filtered[display_cols].rename(columns=renamed),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Close Approach": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "Avg Diameter (m)": st.column_config.NumberColumn(format="%.1f"),
            "Miss Dist (km)": st.column_config.NumberColumn(format="%,.0f"),
            "Miss Dist (LD)": st.column_config.NumberColumn(format="%.2f"),
            "Velocity (km/s)": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption(f"Showing {len(filtered)} of {len(df)} NEOs")


# ──────────────────────────────────────────────
# Main Application
# ──────────────────────────────────────────────
def main():
    """
    Entry point for the Streamlit app.

    Renders the sidebar (API key input, date range picker), fetches
    data on button press, and displays the NEO of the Day, charts,
    and data table in the main content area.
    """

    #  Sidebar controls
    with st.sidebar:
        st.title("☄️ NEO Dashboard")
        st.markdown(
            "Explore Near-Earth Objects using live data from "
            "[NASA's NeoWs API](https://api.nasa.gov/)."
        )
        st.divider()

        # API key input (masked)
        api_key = st.text_input(
            "NASA API Key",
            value=DEFAULT_API_KEY,
            type="password",
            help="Get a free key at https://api.nasa.gov/. "
                 "The DEMO_KEY works but has lower rate limits.",
        )

        # Date range picker, limited to 7 days max by NASA
        st.markdown("#### Date Range")
        today = datetime.today().date()
        start_date = st.date_input(
            "Start date", value=today, max_value=today + timedelta(days=7)
        )
        end_date = st.date_input(
            "End date",
            value=min(today + timedelta(days=6), start_date + timedelta(days=7)),
            min_value=start_date,
            max_value=start_date + timedelta(days=7),
        )

        fetch_btn = st.button(
            "🔍 Fetch NEO Data", type="primary", use_container_width=True
        )

        st.divider()
        st.markdown(
            "**CS-122** — Spring 2026  \n"
            "Anan Belsare & Ethan Nepo"
        )

    # ── Main content area ────────────────────
    st.title("☄️ Near-Earth Object Dashboard")
    st.markdown(
        "Track asteroids and comets approaching Earth using live NASA data. "
        "Select a date range in the sidebar and click **Fetch NEO Data** to begin."
    )

    # Fetch data when the button is pressed, or reuse cached session data
    if fetch_btn or "neo_df" in st.session_state:
        if fetch_btn:
            with st.spinner("Fetching data from NASA NeoWs API…"):
                try:
                    raw = fetch_neo_feed(
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d"),
                        api_key,
                    )
                    df = parse_neo_data(raw)
                    st.session_state["neo_df"] = df
                    st.session_state["element_count"] = raw.get("element_count", len(df))
                except requests.exceptions.HTTPError as e:
                    st.error(f"API error: {e}")
                    return
                except requests.exceptions.ConnectionError:
                    st.error(
                        "Could not connect to NASA API. Check your internet connection."
                    )
                    return
                except Exception as e:
                    st.error(f"Unexpected error: {e}")
                    return

        df = st.session_state.get("neo_df", pd.DataFrame())

        if df.empty:
            st.warning("No NEO data found for this date range.")
            return

        #  Summary metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("NEOs Found", len(df))
        m2.metric("Potentially Hazardous", int(df["is_potentially_hazardous"].sum()))
        m3.metric("Closest Approach", f"{df['miss_distance_lunar'].min():.2f} LD")
        m4.metric("Largest Diameter", f"{df['est_diameter_avg_m'].max():.0f} m")

        st.divider()

        #  NEO of the Day card
        neo_of_day = pick_neo_of_the_day(df, datetime.today())
        if neo_of_day is not None:
            render_neo_of_the_day(neo_of_day)
            st.divider()

        # Tabbed content area
        tab_charts, tab_table = st.tabs(["📊 Visualizations", "🗂️ Data Table"])

        with tab_charts:
            chart_miss_distance_timeline(df)
            st.divider()

            col_left, col_right = st.columns(2)
            with col_left:
                chart_size_comparison(df)
            with col_right:
                chart_hazard_breakdown(df)

            st.divider()
            chart_velocity_vs_size(df)

        with tab_table:
            render_data_table(df)

    else:
        # Landing state before any data is fetched
        st.info(
            "👈 Set a date range in the sidebar and click "
            "**Fetch NEO Data** to get started."
        )


# run the app
if __name__ == "__main__":
    main()
