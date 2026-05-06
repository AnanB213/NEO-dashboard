# ☄️ Near-Earth Object (NEO) Dashboard

An interactive Streamlit dashboard that fetches live close-approach data from NASA's NeoWs API and presents it through intuitive visualizations.

**CS-122 Advanced Python Programming | Section 03 | Spring 2026**  
**Team:** Anan Belsare & Ethan Nepo

---

## Features

- **NEO of the Day** — A deterministically selected asteroid featured with a detailed fact card, refreshed daily.
- **Miss-Distance Timeline** — Interactive scatter plot showing how close each NEO passes to Earth over the selected date range.
- **Size Comparison Chart** — Horizontal bar chart of the 15 largest NEOs by estimated diameter.
- **Hazard Breakdown** — Donut chart and summary metrics splitting objects into potentially hazardous vs. non-hazardous.
- **Velocity vs. Size Plot** — Scatter plot correlating object diameter with approach velocity.
- **Filterable Data Table** — Sort and filter all NEO records by hazard status, minimum diameter, and maximum miss distance.

---

## Prerequisites

- Python 3.9 or higher
- A free NASA API key (optional — `DEMO_KEY` works with lower rate limits)

---

## Installation & Running

1. **Clone the repository:**

   ```bash
   git clone https://github.com/AnanB213/NEO-dashboard.git
   cd NEO-dashboard
   ```

2. **Create and activate a virtual environment (recommended):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate        # macOS / Linux
   # venv\Scripts\activate          # Windows
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Get a NASA API key (optional but recommended):**

   Visit [https://api.nasa.gov/](https://api.nasa.gov/) and sign up for a free key.  
   You can enter the key in the app's sidebar, or replace `DEMO_KEY` in `app.py`.

5. **Run the app:**

   ```bash
   streamlit run app.py
   ```

   The dashboard opens automatically at `http://localhost:8501`.

---

## How to Use

1. Paste your NASA API key into the sidebar (or leave as `DEMO_KEY`).
2. Pick a start and end date (up to 7 days apart).
3. Click **Fetch NEO Data**.
4. Explore the NEO of the Day card, interactive charts, and data table.

---

## Project Structure

```
neo-dashboard/
├── app.py              # Main Streamlit application (single-file)
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## Libraries Used

| Library    | Purpose                                        |
|-----------|------------------------------------------------|
| streamlit | Interactive web UI rendered from Python          |
| requests  | HTTP requests to NASA NeoWs API                  |
| pandas    | Data parsing, structuring, and manipulation      |
| plotly    | Interactive charts (scatter, bar, pie)            |
| datetime  | Date-range logic for filtering close approaches  |
| hashlib   | Deterministic NEO of the Day selection            |

---

## Data Source

All asteroid data is fetched live from [NASA's NeoWs (Near Earth Object Web Service)](https://api.nasa.gov/), a free, open API maintained by NASA's Jet Propulsion Laboratory.
