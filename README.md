# ShopNest — E-commerce Recommendation Prototype


## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

or
```
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```
## Pages

**Storefront (`app.py`)**
Browse/search the product catalog. Click a product to compare recommendations
from all three engines (Content-based, Collaborative, Hybrid), with a slider
to adjust the blend.

**Recommend For User (`pages/1_🎯_Recommend_For_User.py`)**
Pick a random (or specific) customer and see:
- Their purchase history — spend by category, purchase timeline, raw order table (the "evidence")
- Personalized product recommendations, each with a plain-language reason (e.g. *"you've bought 4 smartphones before; similar customers also bought this"*)

## How it works

| Engine | Method |
|---|---|
| Content-based | TF-IDF on category + brand + price tier, cosine similarity |
| Collaborative | Item-based co-purchase similarity + SVD matrix factorization for personalized scores |
| Hybrid | `alpha * content_score + (1 - alpha) * collaborative_score` — falls back to content-only for new/low-history users |

All logic lives in `recommender.py`; `ui_helpers.py` handles styling. Models
are cached (`st.cache_resource`) so the ~435k-row CSV is only processed once
per session.

## Files

```
app.py                              # Storefront + recommendation comparison
pages/Recommend_For_User.py     # Random user + personalized recs
recommender.py                      # Model building & recommendation logic
ui_helpers.py                       # Theme + product card component
data/kz.csv                         # Purchase data
```