import random

import pandas as pd
import plotly.express as px
import streamlit as st

from recommender import (
    build_collab_model,
    build_content_model,
    explain_recommendation,
    get_user_purchase_history,
    load_data,
    recommend_hybrid_user,
)
from ui_helpers import footer, header, inject_theme, product_card, sidebar_brand

st.set_page_config(page_title="ShopNest | Recommend For User", page_icon="🎯", layout="wide")
inject_theme()
sidebar_brand()
header("Recommend for a customer")

with st.spinner("Loading catalog and building recommendation models..."):
    df = load_data()
    content_model = build_content_model(df)
    collab_model = build_collab_model(df)

purchased_by_user = collab_model["purchased_by_user"]
active_user_ids = purchased_by_user.index.tolist()          # users with enough history for CF
all_user_ids = df["user_id"].unique().tolist()               # every user, incl. cold-start ones

st.session_state.setdefault("current_user_id", None)

# --------------------------------------------------------------------------
# User picker
# --------------------------------------------------------------------------
st.markdown('<div class="section-label">Step 1</div>', unsafe_allow_html=True)
st.markdown("#### Choose a customer")

pc1, pc2, pc3 = st.columns([1.3, 1.3, 2])
with pc1:
    if st.button("🎲 Random customer (with history)", width='stretch', type="primary"):
        st.session_state["current_user_id"] = random.choice(active_user_ids)
with pc2:
    if st.button("🎲 Random customer (any)", width='stretch'):
        st.session_state["current_user_id"] = random.choice(all_user_ids)
with pc3:
    manual_id = st.text_input("...or paste a specific user_id", "")
    if manual_id.strip():
        try:
            candidate = int(manual_id.strip())
            if candidate in set(all_user_ids):
                st.session_state["current_user_id"] = candidate
            else:
                st.warning("That user_id isn't in the dataset.")
        except ValueError:
            st.warning("user_id should be numeric.")

if st.session_state["current_user_id"] is None:
    st.session_state["current_user_id"] = random.choice(active_user_ids)

user_id = st.session_state["current_user_id"]
is_active = user_id in set(active_user_ids)

st.success(f"Showing customer **{user_id}** "
           f"{'(enough history for personalized collaborative filtering)' if is_active else '(new / low-activity customer — cold start)'}")

st.divider()

# --------------------------------------------------------------------------
# Purchase history - the "evidence"
# --------------------------------------------------------------------------
st.markdown('<div class="section-label">Step 2 &middot; Evidence</div>', unsafe_allow_html=True)
st.markdown("#### This customer's purchase history")

history = get_user_purchase_history(df, user_id)

if history.empty:
    st.info("No purchase history found for this customer.")
else:
    h1, h2, h3 = st.columns(3)
    h1.metric("Total purchases", len(history))
    h2.metric("Total spend", f"${history['price'].sum():,.2f}")
    h3.metric("Unique categories", history["category_code"].nunique())

    left, right = st.columns([1.3, 1])
    with left:
        st.caption("Spend by category — what this customer actually buys")
        cat_spend = (
            history.assign(category_l1=history["category_code"].str.split(".").str[0])
            .groupby("category_l1", as_index=False)
            .agg(total_spend=("price", "sum"), purchases=("price", "size"))
            .sort_values("total_spend", ascending=False)
        )
        fig = px.bar(
            cat_spend, x="total_spend", y="category_l1", orientation="h",
            color_discrete_sequence=["#0E7C7B"],
            labels={"total_spend": "Total spend ($)", "category_l1": "Category"},
            text="purchases",
        )
        fig.update_traces(texttemplate="%{text} purchase(s)", textposition="outside")
        fig.update_layout(height=320, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width='stretch')

    with right:
        st.caption("Purchases over time — recency & frequency")
        timeline = history.copy()
        timeline["event_time"] = pd.to_datetime(timeline["event_time"])
        fig2 = px.scatter(
            timeline, x="event_time", y="price", size="price", color="category_code",
            labels={"event_time": "Purchase date", "price": "Price ($)"},
        )
        fig2.update_layout(height=320, showlegend=False)
        st.plotly_chart(fig2, width='stretch')

    with st.expander("See every purchased item (raw evidence table)"):
        show_hist = history.copy()
        show_hist["event_time"] = pd.to_datetime(show_hist["event_time"]).dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(
            show_hist.rename(columns={
                "event_time": "Date", "order_id": "Order", "product_id": "Product ID",
                "category_code": "Category", "brand": "Brand", "price": "Price ($)",
            }),
            width='stretch', hide_index=True,
        )

st.divider()

# --------------------------------------------------------------------------
# Recommendations
# --------------------------------------------------------------------------
st.markdown('<div class="section-label">Step 3</div>', unsafe_allow_html=True)
st.markdown("#### Recommended for this customer")

alpha = st.slider(
    "Blend weight (α): 1.0 = based purely on their past purchases (content), "
    "0.0 = based purely on similar customers' behavior (collaborative)",
    0.0, 1.0, 0.5, 0.05,
    help="Cold-start customers (no purchase history) automatically fall back toward "
         "collaborative signal or an empty content profile - try both random buttons above to compare.",
)

recs = recommend_hybrid_user(content_model, collab_model, user_id, top_n=8, alpha=alpha)

if recs.empty:
    st.info("Not enough signal to generate recommendations for this customer yet.")
else:
    cols = st.columns(4)
    for i, (_, r) in enumerate(recs.iterrows()):
        why = explain_recommendation(history, r)
        with cols[i % 4]:
            product_card(r, badge_label=f"match score {r['hybrid_score']:.2f}", why=why)

    with st.expander("How was each recommendation scored? (content vs. collaborative component)"):
        chart_df = recs.melt(
            id_vars=["product_id"],
            value_vars=["content_component", "collab_component"],
            var_name="component", value_name="score",
        )
        chart_df["product_id"] = chart_df["product_id"].astype(str)
        fig3 = px.bar(
            chart_df, x="product_id", y="score", color="component", barmode="group",
            color_discrete_map={"content_component": "#0E7C7B", "collab_component": "#E8A33D"},
            labels={"product_id": "Recommended product", "score": "Component score (normalized)"},
        )
        fig3.update_layout(height=360, legend_title_text="")
        st.plotly_chart(fig3, width='stretch')
        st.caption(
            "**Content component** = how closely the product's category/brand/price profile "
            "matches the average of everything this customer has already bought. "
            "**Collaborative component** = the SVD-predicted preference score learned from "
            "customers with similar purchase patterns. The α slider controls how much each "
            "counts toward the final match score."
        )

footer()