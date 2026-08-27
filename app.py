import pandas as pd
import plotly.express as px
import streamlit as st

from recommender import (
    build_collab_model,
    build_content_model,
    load_data,
    recommend_collab_item,
    recommend_content,
    recommend_hybrid_item,
)
from ui_helpers import footer, header, inject_theme, product_card, sidebar_brand

st.set_page_config(page_title="ShopNest | Recommendation Prototype", page_icon="🛍️", layout="wide")
inject_theme()
sidebar_brand()
header("Storefront")

# --------------------------------------------------------------------------
# Load data & models (cached - only runs once per session)
# --------------------------------------------------------------------------
with st.spinner("Loading catalog and building recommendation models..."):
    df = load_data()
    content_model = build_content_model(df)
    collab_model = build_collab_model(df)

products = content_model["products"]

st.session_state.setdefault("selected_product_id", None)

# --------------------------------------------------------------------------
# Top metrics
# --------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Products in catalog", f"{products.shape[0]:,}")
m2.metric("Customers", f"{df['user_id'].nunique():,}")
m3.metric("Purchase events", f"{df.shape[0]:,}")
m4.metric("Products with CF signal", f"{len(collab_model['prods']):,}",
          help=f"Products bought {collab_model['prods'].size and ''}"
               f"by users with >= {3} purchases, themselves bought >= {5} times "
               f"(same thresholds as collaborative-based.ipynb).")

st.divider()

# --------------------------------------------------------------------------
# Browse catalog
# --------------------------------------------------------------------------
st.markdown('<div class="section-label">Browse the catalog</div>', unsafe_allow_html=True)
st.markdown("#### Find a product")

col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
with col_f1:
    top_categories = sorted(products["category_l1"].dropna().unique())
    chosen_cat = st.selectbox("Category", ["All"] + top_categories)
with col_f2:
    brand_options = sorted(products["brand"].dropna().unique())
    chosen_brand = st.selectbox("Brand", ["All"] + brand_options)
with col_f3:
    search_text = st.text_input("Search by category code, brand, or product ID", "")

filtered = products.copy()
if chosen_cat != "All":
    filtered = filtered[filtered["category_l1"] == chosen_cat]
if chosen_brand != "All":
    filtered = filtered[filtered["brand"] == chosen_brand]
if search_text.strip():
    s = search_text.strip().lower()
    filtered = filtered[
        filtered["category_code"].str.lower().str.contains(s, na=False)
        | filtered["brand"].str.lower().str.contains(s, na=False)
        | filtered["product_id"].astype(str).str.contains(s, na=False)
    ]

filtered = filtered.sort_values("n_purchases", ascending=False)
st.caption(f"{len(filtered):,} product(s) match your filters &middot; showing top sellers first")

PAGE_SIZE = 12
total_pages = max(1, -(-len(filtered) // PAGE_SIZE))
page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
page_slice = filtered.iloc[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

grid_cols = st.columns(4)
for i, (_, row) in enumerate(page_slice.iterrows()):
    with grid_cols[i % 4]:
        product_card(row, badge_label=f"{int(row['n_purchases'])} sold")
        if st.button("View recommendations", key=f"select_{row['product_id']}", width='stretch'):
            st.session_state["selected_product_id"] = int(row["product_id"])

st.divider()

# --------------------------------------------------------------------------
# Recommendation explorer for the selected product
# --------------------------------------------------------------------------
st.markdown('<div class="section-label">Recommendation lab</div>', unsafe_allow_html=True)
st.markdown("#### See what each recommender would suggest")

all_ids = products["product_id"].tolist()
default_idx = 0
if st.session_state["selected_product_id"] in all_ids:
    default_idx = all_ids.index(st.session_state["selected_product_id"])

picked_id = st.selectbox(
    "Query product",
    all_ids,
    index=default_idx,
    format_func=lambda pid: f"{pid} — {products.loc[pid, 'category_code']} / {products.loc[pid, 'brand']} "
                             f"(${products.loc[pid, 'price']:.2f})",
)
st.session_state["selected_product_id"] = picked_id

query_row = products.loc[picked_id]
qc1, qc2 = st.columns([1, 3])
with qc1:
    product_card(query_row, badge_label="Query product")
with qc2:
    st.write(
        f"**Category:** {query_row['category_code']}  \n"
        f"**Brand:** {query_row['brand'].title()}  \n"
        f"**Price:** ${query_row['price']:.2f}  \n"
        f"**Times purchased:** {int(query_row['n_purchases'])}"
    )
    has_cf = picked_id in collab_model["prod_to_idx"].index
    if not has_cf:
        st.caption("⚠️ This product doesn't have enough purchase history for collaborative "
                   "filtering yet - content-based results still work fine (this is the "
                   "classic 'cold start' problem hybrid filtering is designed to solve).")

tab_content, tab_collab, tab_hybrid = st.tabs(
    ["📚 Content-based", "🤝 Collaborative (also bought)", "🧬 Hybrid blend"]
)

with tab_content:
    st.caption("Similar **product attributes**: category, brand, price tier (TF-IDF + cosine similarity).")
    rec_c = recommend_content(content_model, picked_id, top_n=8)
    if rec_c.empty:
        st.info("No recommendations available for this product.")
    else:
        cols = st.columns(4)
        for i, (_, r) in enumerate(rec_c.iterrows()):
            with cols[i % 4]:
                product_card(r, badge_label=f"{r['similarity']:.0%} similar")

with tab_collab:
    st.caption("Products **frequently bought by the same customers** as this one (item-based collaborative filtering).")
    rec_cf = recommend_collab_item(collab_model, picked_id, top_n=8)
    if rec_cf.empty:
        st.info("Not enough co-purchase history for this product - try one with more sales, "
                 "or check the Hybrid tab which falls back to content similarity.")
    else:
        cols = st.columns(4)
        for i, (_, r) in enumerate(rec_cf.iterrows()):
            with cols[i % 4]:
                product_card(r, badge_label=f"{r['similarity']:.0%} co-bought")

with tab_hybrid:
    alpha = st.slider(
        "Blend weight (α): 1.0 = pure content-based, 0.0 = pure collaborative",
        0.0, 1.0, 0.5, 0.05,
    )
    rec_h = recommend_hybrid_item(content_model, collab_model, picked_id, top_n=8, alpha=alpha)
    if rec_h.empty:
        st.info("No recommendations available for this product.")
    else:
        cols = st.columns(4)
        for i, (_, r) in enumerate(rec_h.iterrows()):
            with cols[i % 4]:
                product_card(r, badge_label=f"score {r['hybrid_score']:.2f}")

        with st.expander("See the content vs. collaborative components behind the hybrid score"):
            chart_df = rec_h.melt(
                id_vars=["product_id"],
                value_vars=["content_component", "collab_component"],
                var_name="component",
                value_name="score",
            )
            chart_df["product_id"] = chart_df["product_id"].astype(str)
            fig = px.bar(
                chart_df, x="product_id", y="score", color="component", barmode="group",
                color_discrete_map={"content_component": "#0E7C7B", "collab_component": "#E8A33D"},
                labels={"product_id": "Recommended product", "score": "Component similarity"},
            )
            fig.update_layout(height=360, legend_title_text="")
            st.plotly_chart(fig, width='stretch')

st.divider()
st.page_link("pages/Recommend_For_User.py", label="➡️ Go to: pick a random customer and see their personal recommendations", icon="🎯")
footer()