from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors

DATA_PATH = Path(__file__).resolve().parent / "kz.csv"

MIN_USER_PURCHASES = 3       # same thresholds as collaborative-based.ipynb
MIN_PRODUCT_PURCHASES = 5
N_COMPONENTS = 30            # SVD latent factors


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_data(path: str = DATA_PATH) -> pd.DataFrame:
    """Load the raw purchase-event log (one row per purchase event)."""
    df = pd.read_csv(path)
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True, errors="coerce")
    df["brand"] = df["brand"].fillna("unknown").str.lower().str.strip()
    return df


# --------------------------------------------------------------------------
# Content-based model  (content-based.ipynb)
# --------------------------------------------------------------------------

def _split_category(code: str) -> tuple[str, str, str]:
    parts = str(code).split(".")
    parts += [parts[-1]] * (3 - len(parts))
    return parts[0], parts[1], parts[2]


@st.cache_resource(show_spinner=False)
def build_content_model(_df: pd.DataFrame):
    """Build the product catalog + TF-IDF content vectors + NN index."""
    products = (
        _df.groupby("product_id")
        .agg(
            category_id=("category_id", "first"),
            category_code=("category_code", "first"),
            brand=("brand", lambda s: s.mode().iat[0] if not s.mode().empty else "unknown"),
            price=("price", "mean"),
            n_purchases=("product_id", "size"),
        )
        .reset_index()
    )
    products["brand"] = products["brand"].fillna("unknown").str.lower().str.strip()
    products["price"] = products["price"].round(2)

    products[["category_l1", "category_l2", "category_l3"]] = products["category_code"].apply(
        lambda c: pd.Series(_split_category(c))
    )
    products["price_tier"] = pd.qcut(
        products["price"], q=4, labels=["budget", "mid", "premium", "luxury"], duplicates="drop"
    )
    products["content"] = (
        products["category_l1"] + " " +
        products["category_l2"] + " " +
        products["category_l3"] + " " +
        (products["brand"] + " ") * 2 +
        products["price_tier"].astype(str)
    )

    tfidf = TfidfVectorizer(token_pattern=r"[a-zA-Z0-9]+")
    tfidf_matrix = tfidf.fit_transform(products["content"])

    nn_model = NearestNeighbors(metric="cosine", algorithm="brute")
    nn_model.fit(tfidf_matrix)

    product_index = pd.Series(products.index, index=products["product_id"])

    return {
        "products": products.set_index("product_id", drop=False),
        "tfidf": tfidf,
        "tfidf_matrix": tfidf_matrix,
        "nn_model": nn_model,
        "product_index": product_index,
    }


def recommend_content(content_model: dict, product_id: int, top_n: int = 10) -> pd.DataFrame:
    """'Similar products' - pure content-based (category / brand / price)."""
    idx_map = content_model["product_index"]
    if product_id not in idx_map.index:
        return pd.DataFrame()

    idx = idx_map[product_id]
    tfidf_matrix = content_model["tfidf_matrix"]
    distances, indices = content_model["nn_model"].kneighbors(
        tfidf_matrix[idx], n_neighbors=min(top_n + 1, tfidf_matrix.shape[0])
    )
    products = content_model["products"]
    rec_ids = products.iloc[indices[0]]["product_id"].values
    result = products.iloc[indices[0]].copy()
    result["similarity"] = 1 - distances[0]
    result = result[result["product_id"] != product_id]
    cols = ["product_id", "category_code", "brand", "price", "price_tier", "similarity"]
    return result[cols].reset_index(drop=True).head(top_n)


# --------------------------------------------------------------------------
# Collaborative model  (collaborative-based.ipynb)
# --------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def build_collab_model(_df: pd.DataFrame):
    """Build the filtered user-item interaction matrix, item-based NN and SVD."""
    user_counts = _df["user_id"].value_counts()
    prod_counts = _df["product_id"].value_counts()

    active_users = user_counts[user_counts >= MIN_USER_PURCHASES].index
    active_products = prod_counts[prod_counts >= MIN_PRODUCT_PURCHASES].index

    interactions = _df[
        _df["user_id"].isin(active_users) & _df["product_id"].isin(active_products)
    ].copy()

    product_info = (
        _df.groupby("product_id")
        .agg(
            category_code=("category_code", "first"),
            brand=("brand", lambda s: s.mode().iat[0] if not s.mode().empty else "unknown"),
            price=("price", "mean"),
        )
        .reset_index()
    )
    product_info["brand"] = product_info["brand"].fillna("unknown").str.lower().str.strip()
    product_info["price"] = product_info["price"].round(2)
    product_info = product_info.set_index("product_id")

    prods = pd.Index(sorted(interactions["product_id"].unique()), name="product_id")
    users = pd.Index(sorted(interactions["user_id"].unique()), name="user_id")
    user_to_idx = pd.Series(np.arange(len(users)), index=users)
    prod_to_idx = pd.Series(np.arange(len(prods)), index=prods)

    rows = interactions["product_id"].map(prod_to_idx).values
    cols = interactions["user_id"].map(user_to_idx).values
    data = np.ones(len(interactions), dtype=np.float32)
    item_user = csr_matrix((data, (rows, cols)), shape=(len(prods), len(users)))

    item_nn = NearestNeighbors(metric="cosine", algorithm="brute")
    item_nn.fit(item_user)

    user_item = item_user.T.tocsr()
    svd = TruncatedSVD(n_components=min(N_COMPONENTS, min(user_item.shape) - 1), random_state=42)
    user_factors = svd.fit_transform(user_item)
    item_factors = svd.components_.T

    purchased_by_user = interactions.groupby("user_id")["product_id"].apply(set)

    return {
        "interactions": interactions,
        "product_info": product_info,
        "prods": prods,
        "users": users,
        "user_to_idx": user_to_idx,
        "prod_to_idx": prod_to_idx,
        "item_user": item_user,
        "item_nn": item_nn,
        "user_factors": user_factors,
        "item_factors": item_factors,
        "purchased_by_user": purchased_by_user,
        "user_counts": user_counts,
        "prod_counts": prod_counts,
    }


def recommend_collab_item(collab_model: dict, product_id: int, top_n: int = 10) -> pd.DataFrame:
    """'Customers who bought this also bought' - item-based CF."""
    prod_to_idx = collab_model["prod_to_idx"]
    if product_id not in prod_to_idx.index:
        return pd.DataFrame()

    idx = prod_to_idx[product_id]
    item_user = collab_model["item_user"]
    distances, indices = collab_model["item_nn"].kneighbors(
        item_user[idx], n_neighbors=min(top_n + 1, item_user.shape[0])
    )
    prods = collab_model["prods"]
    product_info = collab_model["product_info"]
    rec_ids = prods[indices[0]]
    result = product_info.loc[rec_ids].copy()
    result["product_id"] = rec_ids
    result["similarity"] = 1 - distances[0]
    result = result[result["product_id"] != product_id]
    cols = ["product_id", "category_code", "brand", "price", "similarity"]
    return result[cols].reset_index(drop=True).head(top_n)


def recommend_collab_user(collab_model: dict, user_id: int, top_n: int = 10) -> pd.DataFrame:
    """Personalized recommendations for a user via SVD latent factors."""
    user_to_idx = collab_model["user_to_idx"]
    if user_id not in user_to_idx.index:
        return pd.DataFrame()

    u_idx = user_to_idx[user_id]
    scores = collab_model["user_factors"][u_idx] @ collab_model["item_factors"].T

    purchased_by_user = collab_model["purchased_by_user"]
    already_bought = purchased_by_user.get(user_id, set())
    if already_bought:
        already_idx = collab_model["prod_to_idx"][list(already_bought)].values
        scores = scores.copy()
        scores[already_idx] = -np.inf

    top_n = min(top_n, len(scores) - 1)
    top_idx = np.argpartition(-scores, top_n)[:top_n]
    top_idx = top_idx[np.argsort(-scores[top_idx])]

    prods = collab_model["prods"]
    product_info = collab_model["product_info"]
    rec_ids = prods[top_idx]
    result = product_info.loc[rec_ids].copy()
    result["product_id"] = rec_ids
    result["predicted_score"] = scores[top_idx]
    cols = ["product_id", "category_code", "brand", "price", "predicted_score"]
    return result[cols].reset_index(drop=True)


# --------------------------------------------------------------------------
# Hybrid model  (hybrid.ipynb)
# --------------------------------------------------------------------------

def recommend_hybrid_item(
    content_model: dict, collab_model: dict, product_id: int, top_n: int = 10, alpha: float = 0.5
) -> pd.DataFrame:
    """Weighted blend of content similarity + collaborative co-purchase similarity."""
    products = content_model["products"]
    if product_id not in products.index:
        return pd.DataFrame()

    tfidf_matrix = content_model["tfidf_matrix"]
    c_idx = content_model["product_index"][product_id]
    content_sim = cosine_similarity(tfidf_matrix[c_idx], tfidf_matrix).flatten()
    content_sim = pd.Series(content_sim, index=products["product_id"])

    prod_to_idx = collab_model["prod_to_idx"]
    if product_id in prod_to_idx.index:
        cf_idx = prod_to_idx[product_id]
        item_user = collab_model["item_user"]
        collab_sim = cosine_similarity(item_user[cf_idx], item_user).flatten()
        collab_sim = pd.Series(collab_sim, index=collab_model["prods"])
    else:
        collab_sim = pd.Series(dtype=float)
    collab_sim = collab_sim.reindex(content_sim.index, fill_value=0.0)

    hybrid_score = alpha * content_sim + (1 - alpha) * collab_sim
    hybrid_score = hybrid_score.drop(index=product_id, errors="ignore")

    top = hybrid_score.sort_values(ascending=False).head(top_n)
    result = products.loc[top.index, ["category_code", "brand", "price"]].copy()
    result["product_id"] = top.index
    result["hybrid_score"] = top.values
    result["content_component"] = content_sim.loc[top.index].values
    result["collab_component"] = collab_sim.loc[top.index].values
    cols = ["product_id", "category_code", "brand", "price", "hybrid_score", "content_component", "collab_component"]
    return result[cols].reset_index(drop=True)


def recommend_hybrid_user(
    content_model: dict, collab_model: dict, user_id: int, top_n: int = 10, alpha: float = 0.5
) -> pd.DataFrame:
    """
    Personalized hybrid recommendations for a user.

    - Collaborative component: SVD predicted score (0 if user has no CF profile,
      e.g. fewer than MIN_USER_PURCHASES purchases - a "cold" user).
    - Content component: average TF-IDF similarity between every catalog product
      and the products the user has already purchased (their "taste profile").
    This lets the blend degrade gracefully to pure content-based for new/low-activity
    users, and pure collaborative for users with lots of history, controlled by alpha.
    """
    products = content_model["products"]
    all_ids = products["product_id"].values

    # --- collaborative component ---
    user_to_idx = collab_model["user_to_idx"]
    if user_id in user_to_idx.index:
        u_idx = user_to_idx[user_id]
        raw_scores = collab_model["user_factors"][u_idx] @ collab_model["item_factors"].T
        collab_scores = pd.Series(raw_scores, index=collab_model["prods"])
        # normalize to [0, 1] so it's comparable to cosine content similarity
        rng = collab_scores.max() - collab_scores.min()
        if rng > 0:
            collab_scores = (collab_scores - collab_scores.min()) / rng
    else:
        collab_scores = pd.Series(dtype=float)
    collab_scores = collab_scores.reindex(all_ids, fill_value=0.0)

    # --- content component: similarity to the user's purchase history ---
    history_ids = get_user_history_ids(collab_model, user_id)
    tfidf_matrix = content_model["tfidf_matrix"]
    product_index = content_model["product_index"]
    valid_hist_idx = [product_index[pid] for pid in history_ids if pid in product_index.index]

    if valid_hist_idx:
        user_profile_vec = tfidf_matrix[valid_hist_idx].mean(axis=0)
        user_profile_vec = np.asarray(user_profile_vec)
        content_scores = cosine_similarity(user_profile_vec, tfidf_matrix).flatten()
        content_scores = pd.Series(content_scores, index=products["product_id"])
    else:
        content_scores = pd.Series(0.0, index=products["product_id"])

    hybrid_score = alpha * content_scores + (1 - alpha) * collab_scores
    hybrid_score = hybrid_score.drop(index=[i for i in history_ids if i in hybrid_score.index])

    top = hybrid_score.sort_values(ascending=False).head(top_n)
    result = products.loc[top.index, ["category_code", "brand", "price"]].copy()
    result["product_id"] = top.index
    result["hybrid_score"] = top.values
    result["content_component"] = content_scores.reindex(top.index).values
    result["collab_component"] = collab_scores.reindex(top.index).values
    cols = ["product_id", "category_code", "brand", "price", "hybrid_score", "content_component", "collab_component"]
    return result[cols].reset_index(drop=True)


# --------------------------------------------------------------------------
# User purchase history helpers (the "evidence" for a recommendation)
# --------------------------------------------------------------------------

def get_user_history_ids(collab_model: dict, user_id: int) -> set:
    return collab_model["purchased_by_user"].get(user_id, set())


def get_user_purchase_history(df: pd.DataFrame, user_id: int) -> pd.DataFrame:
    """Full chronological purchase history for one user, from the raw log."""
    hist = df[df["user_id"] == user_id].copy()
    hist = hist.sort_values("event_time")
    hist = hist.drop_duplicates(subset=["order_id", "product_id"])
    return hist[["event_time", "order_id", "product_id", "category_code", "brand", "price"]]


def explain_recommendation(
    history: pd.DataFrame, rec_row: pd.Series
) -> str:
    """Plain-language reason a product was recommended, used as on-page evidence."""
    reasons = []

    if not history.empty:
        hist_categories = history["category_code"].value_counts()
        hist_brands = history["brand"].value_counts()
        rec_l1 = str(rec_row["category_code"]).split(".")[0]
        hist_l1 = history["category_code"].astype(str).str.split(".").str[0]

        if rec_row["category_code"] in hist_categories.index:
            n = hist_categories[rec_row["category_code"]]
            reasons.append(f"you've bought {n} item(s) in **{rec_row['category_code']}** before")
        elif rec_l1 in hist_l1.values:
            reasons.append(f"it's in **{rec_l1}**, a category you shop often")

        if rec_row["brand"] in hist_brands.index and rec_row["brand"] != "unknown":
            reasons.append(f"you've bought **{rec_row['brand']}** products before")

    collab_component = rec_row.get("collab_component", None)
    content_component = rec_row.get("content_component", None)
    if collab_component is not None and content_component is not None:
        if collab_component > content_component:
            reasons.append("customers with a similar purchase history also bought this")
        elif content_component > 0 and not reasons:
            reasons.append("it closely matches the products in your history")

    if not reasons:
        reasons.append("it's a popular match based on your overall shopping pattern")

    return "; ".join(reasons[:2]).capitalize()
