"""
app.py  -  BreatheSafe: Air Pollution and Respiratory Diseases Analysis (Nagpur, Maharashtra)

Run with:   streamlit run app.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analysis as an

# ---------------------------------------------------------------------------
# Page setup and file locations
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="BreatheSafe",
    page_icon="",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
SAMPLE_AIR = BASE_DIR / "data" / "sample_air_pollution.csv"
SAMPLE_HOSPITAL = BASE_DIR / "data" / "sample_hospital_admissions.csv"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def read_csv_safely(source, label: str) -> pd.DataFrame:
    """Read a CSV from a path or an uploaded file. Raises DataError if it fails."""
    try:
        if hasattr(source, "seek"):
            source.seek(0)  # uploaded files must be rewound on every rerun
        df = pd.read_csv(source)
    except pd.errors.EmptyDataError:
        raise an.DataError(f"The {label} file is empty.")
    except pd.errors.ParserError:
        raise an.DataError(f"The {label} file could not be read. Is it a valid CSV file?")
    except UnicodeDecodeError:
        raise an.DataError(f"The {label} file is not a text CSV file (encoding problem).")
    except Exception as error:  # last safety net
        raise an.DataError(f"The {label} file could not be loaded: {error}")

    if df.empty:
        raise an.DataError(f"The {label} file has no rows.")
    return df


def load_data(air_source, hospital_source):
    """Read, clean and combine both files."""
    air_raw = read_csv_safely(air_source, "air pollution")
    hospital_raw = read_csv_safely(hospital_source, "hospital admissions")

    air_monthly, air_notes = an.clean_air_data(air_raw)
    hospital_monthly, hospital_notes = an.clean_hospital_data(hospital_raw)
    merged = an.merge_monthly(air_monthly, hospital_monthly)
    return air_monthly, hospital_monthly, merged, air_notes + hospital_notes


# ---------------------------------------------------------------------------
# Sidebar: CSV upload
# ---------------------------------------------------------------------------
st.sidebar.header("📂 Load your data")

uploaded_air = st.sidebar.file_uploader("Air pollution CSV", type="csv", key="air")
uploaded_hospital = st.sidebar.file_uploader("Hospital admissions CSV", type="csv", key="hospital")

with st.sidebar.expander("Required CSV format"):
    st.markdown(
        """
**Air pollution CSV**

| date | aqi | pm25 | pm10 |
|---|---|---|---|
| 2024-01-01 | 150 | 80 | 160 |

**Hospital admissions CSV**

| date | age_group | admissions |
|---|---|---|
| 2024-01-01 | Children (0-14) | 120 |

Daily or monthly rows both work. Dates should look like `YYYY-MM-DD`.
        """
    )

using_sample = True
if uploaded_air is not None and uploaded_hospital is not None:
    air_source, hospital_source = uploaded_air, uploaded_hospital
    using_sample = False
else:
    air_source, hospital_source = SAMPLE_AIR, SAMPLE_HOSPITAL
    if uploaded_air is not None or uploaded_hospital is not None:
        st.sidebar.warning("Please upload **both** files to use your own data. Showing sample data for now.")

# ---------------------------------------------------------------------------
# Load data (stop politely if something is wrong)
# ---------------------------------------------------------------------------
try:
    air_m, hospital_m, merged, cleaning_notes = load_data(air_source, hospital_source)
except an.DataError as error:
    st.title("BreatheSafe")
    st.error(f"{error}")
    st.info("Fix the file and upload it again, or remove the uploaded files to use the sample data.")
    st.stop()

# ---------------------------------------------------------------------------
# Title and introduction
# ---------------------------------------------------------------------------

st.title("🌿 BreatheSafe")
st.markdown("### Air Pollution & Respiratory Health Analytics")
st.caption("📍 Study Area: Nagpur, Maharashtra, India")

st.markdown(
    "Explore air quality trends, respiratory hospital admissions, "
    "and the relationship between pollution and public health."
)

st.divider()


# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------
corr_df = an.correlation_table(merged)
age_summary = an.age_group_summary(hospital_m)
age_corr = an.age_group_correlation(air_m, hospital_m)

pm25_row = corr_df[corr_df["Pollutant"] == "PM2.5"].iloc[0]
headline_r = pm25_row["Pearson r"]

# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------

st.header("Dashboard")

c1, c2, c3, c4 = st.columns(4)

with c1:
    with st.container(border=True):
        st.metric(
            "Average AQI",
            f"{air_m['aqi'].mean():.0f}"
        )

with c2:
    with st.container(border=True):
        st.metric(
            "Average PM2.5",
            f"{air_m['pm25'].mean():.1f} µg/m³"
        )

with c3:
    with st.container(border=True):
        st.metric(
            "Respiratory Admissions",
            f"{int(hospital_m['admissions'].sum()):,}"
        )

with c4:
    with st.container(border=True):
        st.metric(
            "PM2.5 Correlation",
            "N/A" if np.isnan(headline_r)
            else f"{headline_r:.2f}"
        )

# ---------------------------------------------------------------------------
# Trend charts
# ---------------------------------------------------------------------------
st.header("📈 Trends over time")

air_long = air_m.melt(
    id_vars="month",
    value_vars=["aqi", "pm25", "pm10"],
    var_name="Indicator",
    value_name="Value",
)
air_long["Indicator"] = air_long["Indicator"].map({"aqi": "AQI", "pm25": "PM2.5", "pm10": "PM10"})
fig_air = px.line(
    air_long,
    x="month",
    y="Value",
    color="Indicator",
    title="Monthly average air pollution",
    labels={"month": "Month", "Value": "Level (AQI / µg/m³)"},
)
st.plotly_chart(fig_air)

total_by_month = merged[["month", "admissions"]]
fig_adm = px.line(
    total_by_month,
    x="month",
    y="admissions",
    title="Monthly respiratory hospital admissions (all age groups)",
    labels={"month": "Month", "admissions": "Admissions"},
    markers=True,
)
fig_adm.update_traces(line_color="#d62728")
st.plotly_chart(fig_adm)

# ---------------------------------------------------------------------------
# Age group comparison
# ---------------------------------------------------------------------------
st.header("Admissions by age group")
fig_age = px.bar(
    age_summary,
    x="age_group",
    y="admissions",
    color="age_group",
    text_auto=True,
    title="Total respiratory admissions by age group",
    labels={"age_group": "Age group", "admissions": "Total admissions"},
)
fig_age.update_layout(showlegend=False)
st.plotly_chart(fig_age)

top_group = age_summary.iloc[0]
st.info(
    f"Most admissions come from **{top_group['age_group']}** "
    f"({int(top_group['admissions']):,} admissions, {top_group['share_percent']}% of the total)."
)


# ---------------------------------------------------------------------------
# Correlation results and key findings
# ---------------------------------------------------------------------------
st.header("🔗 Correlation results and key findings")

show_corr = corr_df.copy()
show_corr["Pearson r"] = show_corr["Pearson r"].map(lambda v: "n/a" if np.isnan(v) else f"{v:.3f}")
show_corr["p-value"] = corr_df["p-value"].map(an.format_p)
st.write("**Pearson correlation with monthly total admissions**")
st.dataframe(show_corr, hide_index=True)

st.write("**Scatter plot**")
pollutant_choice = st.selectbox("Choose a pollutant", ["PM2.5", "PM10", "AQI"])
col_name = {"PM2.5": "pm25", "PM10": "pm10", "AQI": "aqi"}[pollutant_choice]

fig_scatter = px.scatter(
    merged,
    x=col_name,
    y="admissions",
    hover_data={"month": "|%b %Y"},
    labels={col_name: pollutant_choice, "admissions": "Monthly admissions"},
    title=f"{pollutant_choice} vs monthly respiratory admissions",
)
if merged[col_name].nunique() > 1:  # draw a simple straight trend line
    slope, intercept = np.polyfit(merged[col_name], merged["admissions"], 1)
    x_line = np.array([merged[col_name].min(), merged[col_name].max()])
    fig_scatter.add_trace(
        go.Scatter(x=x_line, y=slope * x_line + intercept, mode="lines", name="Trend line")
    )
st.plotly_chart(fig_scatter)

st.write("**Correlation of PM2.5 with admissions for each age group**")
show_age_corr = age_corr.copy()
show_age_corr["Pearson r (PM2.5)"] = age_corr["Pearson r (PM2.5)"].map(
    lambda v: "n/a" if np.isnan(v) else f"{v:.3f}"
)
show_age_corr["p-value"] = age_corr["p-value"].map(an.format_p)
st.dataframe(show_age_corr, hide_index=True)

# Key findings, written automatically from the numbers
st.subheader("Key findings")
valid = corr_df.dropna(subset=["Pearson r"])
if valid.empty:
    st.write("• Not enough varied data to calculate a correlation.")
else:
    best = valid.loc[valid["Pearson r"].abs().idxmax()]
    st.write(
        f"• **{best['Pollutant']}** has the strongest relationship with admissions "
        f"(r = {best['Pearson r']:.2f}, {best['Strength'].lower()} correlation, "
        f"p-value {an.format_p(best['p-value'])})."
    )

peak_air = air_m.loc[air_m["pm25"].idxmax()]
peak_adm = merged.loc[merged["admissions"].idxmax()]
st.write(
    f"• PM2.5 was highest in **{peak_air['month']:%B %Y}** ({peak_air['pm25']:.1f} µg/m³); "
    f"admissions peaked in **{peak_adm['month']:%B %Y}** ({int(peak_adm['admissions']):,})."
)
st.write(
    f"• The most affected age group (by number of admissions) is **{top_group['age_group']}**."
)

# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

st.header("Air Pollution Reduction Plan")
st.caption("Practical steps for cleaner air and better respiratory health.")

r1, r2 = st.columns(2)

with r1:
    with st.container(border=True):
        st.subheader("Vehicle Emissions")
        st.markdown("""
        - Regular PUC checks
        - Promote EVs and cleaner fuels
        - Improve bus services
        - Promote walking and cycling
        """)

with r2:
    with st.container(border=True):
        st.subheader("Industrial Control")
        st.markdown("""
        - Install emission-control filters
        - Monitor factory emissions
        - Enforce pollution standards
        """)

r3, r4 = st.columns(2)

with r3:
    with st.container(border=True):
        st.subheader("Green Spaces")
        st.markdown("""
        - Plant native trees
        - Protect parks and forests
        - Control road and soil dust
        """)

with r4:
    with st.container(border=True):
        st.subheader("Community Actions")
        st.markdown("""
        - Prevent open burning of waste.
        - Control dust at construction sites.
        - Share health alerts on high-pollution days.
        """)

# ---------------------------------------------------------------------------
# Raw data preview and footer
# ---------------------------------------------------------------------------
with st.expander("🔍 View cleaned monthly data"):
    st.write("**Air pollution (monthly average)**")
    st.dataframe(air_m, hide_index=True)
    st.write("**Hospital admissions (monthly total per age group)**")
    st.dataframe(hospital_m, hide_index=True)

st.divider()

