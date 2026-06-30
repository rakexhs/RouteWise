"""RouteWise observability dashboard."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from app.config import get_settings

st.set_page_config(page_title="RouteWise Dashboard", layout="wide")
st.title("RouteWise Gateway Dashboard")

settings = get_settings()
engine = create_engine(settings.database_url)


@st.cache_data(ttl=30)
def load_requests() -> pd.DataFrame:
    try:
        df = pd.read_sql("SELECT * FROM request_logs ORDER BY timestamp DESC", engine)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception:
        return pd.DataFrame()


df = load_requests()

if df.empty:
    st.warning("No request data yet. Run `make demo` or send API requests.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Requests", len(df))
col2.metric("Avg Latency (ms)", f"{df['latency_ms'].mean():.1f}")
col3.metric("Total Cost ($)", f"{df['estimated_cost'].sum():.4f}")
cache_hits = df[df["cache_status"].isin(["exact_hit", "semantic_hit"])]
col4.metric("Cache Hit Rate", f"{len(cache_hits)/len(df)*100:.1f}%")

st.subheader("Request Volume")
volume = df.set_index("timestamp").resample("1min").size()
st.line_chart(volume)

st.subheader("Latency Distribution")
st.bar_chart(df["latency_ms"])

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Route Breakdown")
    st.bar_chart(df["model_used"].value_counts())
with col_b:
    st.subheader("Cost by Model")
    cost_by_model = df.groupby("model_used")["estimated_cost"].sum()
    st.bar_chart(cost_by_model)

st.subheader("Feature Breakdown")
if "feature" in df.columns:
    feature_counts = df["feature"].fillna("unknown").value_counts()
    st.bar_chart(feature_counts)

st.subheader("Cache Status")
st.bar_chart(df["cache_status"].value_counts())

st.subheader("Provider Health / Circuit Breaker")
circuit_path = Path("data/circuit_state.json")
if circuit_path.exists():
    state = json.loads(circuit_path.read_text())
    st.json(state)
else:
    st.info("Circuit state snapshot not yet available.")

st.subheader("Recent Requests")
st.dataframe(df.head(50))

st.subheader("Evaluation Results")
eval_path = Path("reports/evaluation_results.md")
if eval_path.exists():
    st.markdown(eval_path.read_text())
else:
    st.info("Run `make eval` to generate evaluation results.")
