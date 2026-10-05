import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
from PIL import Image, ImageDraw
import plotly.express as px

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Universal Bar Chart Race Generator",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Universal Animated Bar Chart Race")
st.write(
    "Upload any wide or long CSV dataset containing Brands, Countries, or mixed Entities with working image/logo URLs."
)


# ---------------------------------------------------------
# 1. HELPER: DOWNLOAD AND PROCESS IMAGE
# ---------------------------------------------------------
def load_and_process_image(url):
    """
    Downloads an image from any valid URL and converts it to PIL RGBA format.
    Supports PNG, SVG/PNG conversion, JPG, WebP, etc.
    """
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return None

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/115.0.0.0 Safari/537.36'
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert('RGBA')
            return img
    except Exception:
        pass
    return None


# ---------------------------------------------------------
# 2. UNIVERSAL IMAGE & ENTITY PARSER (CATEGORY AGNOSTIC)
# ---------------------------------------------------------
def fetch_universal_images(df):
    """
    Scans any dataframe and builds a map of Entity Name -> Image object.
    Works universally across Countries, Brands, Companies, or mixed datasets.
    """
    image_dict = {}

    clean_cols = {col: str(col).strip().lower() for col in df.columns}

    # Identify image/logo/flag URL column
    url_col_candidates = [
        'logo', 'flag', 'image', 'icon', 'url', 'photo', 
        'avatar', 'logo (optional)', 'image url', 'flag url'
    ]
    matched_url_col = None
    for col, lower_col in clean_cols.items():
        if lower_col in url_col_candidates or any(k in lower_col for k in ['logo', 'flag', 'image', 'url']):
            matched_url_col = col
            break

    # Identify entity name column (Brand, Country, Name, Company, etc.)
    entity_col_candidates = ['brand', 'country', 'name', 'label', 'company', 'entity', 'category']
    matched_entity_col = None
    for col, lower_col in clean_cols.items():
        if lower_col in entity_col_candidates:
            matched_entity_col = col
            break

    # Fallback to first non-numeric column if no matching header found
    if not matched_entity_col:
        for col in df.columns:
            if not str(col).strip().isdigit() and col != matched_url_col:
                matched_entity_col = col
                break

    if not matched_entity_col:
        matched_entity_col = df.columns[0]

    # Process each row independently (category agnostic)
    for _, row in df.iterrows():
        entity_name = str(row[matched_entity_col]).strip()
        if not entity_name or entity_name.lower() in ['nan', 'none', '']:
            continue

        img_url = (
            str(row[matched_url_col]).strip()
            if matched_url_col and pd.notna(row[matched_url_col])
            else None
        )

        img = load_and_process_image(img_url) if img_url else None
        if img:
            image_dict[entity_name] = img

    return image_dict, matched_entity_col, matched_url_col


# ---------------------------------------------------------
# 3. UNIVERSAL DATA PREPARATION & MELTING
# ---------------------------------------------------------
def prepare_wide_or_long_df(df):
    """
    Reshapes wide-format or long-format datasets automatically,
    preserving entity identity regardless of metadata columns.
    """
    year_cols = [col for col in df.columns if str(col).strip().isdigit()]
    meta_cols = [col for col in df.columns if col not in year_cols]

    image_dict, entity_col, url_col = fetch_universal_images(df)

    if year_cols:
        # Wide Format -> Melt into Long Format
        long_df = df.melt(
            id_vars=meta_cols,
            value_vars=year_cols,
            var_name='Date',
            value_name='Value'
        )
        long_df['Entity'] = long_df[entity_col]
        long_df['Date'] = pd.to_numeric(long_df['Date'], errors='coerce')
        long_df['Value'] = pd.to_numeric(long_df['Value'], errors='coerce').fillna(0)
        return long_df, image_dict, 'Entity'
    else:
        # Long Format
        long_df = df.copy()
        long_df['Entity'] = long_df[entity_col]
        if 'Date' in long_df.columns:
            long_df['Date'] = pd.to_numeric(long_df['Date'], errors='coerce')
        if 'Value' in long_df.columns:
            long_df['Value'] = pd.to_numeric(long_df['Value'], errors='coerce').fillna(0)
        return long_df, image_dict, 'Entity'


# ---------------------------------------------------------
# 4. STREAMLIT APP INTERFACE & VISUALIZATION
# ---------------------------------------------------------
uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)

    st.subheader("📋 Raw Data Preview")
    st.dataframe(df_raw.head())

    with st.spinner("Parsing entities and fetching logos/images..."):
        df_processed, image_map, entity_col_name = prepare_wide_or_long_df(df_raw)

    st.success(f"Successfully processed dataset. Found images for {len(image_map)} entities!")

    # Display image loading summary
    if image_map:
        st.write("### 🖼️ Loaded Entities & Logos")
        cols = st.columns(min(len(image_map), 6))
        for i, (entity, img) in enumerate(image_map.items()):
            with cols[i % 6]:
                st.image(img, caption=entity, width=70)

    # Visualization Setup
    st.subheader("📈 Animated Race Chart")

    top_n = st.slider("Number of Top Entities to Display", min_value=5, max_value=20, value=10)

    # Sort data per timestamp
    df_sorted = (
        df_processed.groupby(['Date', 'Entity'], as_index=False)['Value']
        .sum()
        .sort_values(['Date', 'Value'], ascending=[True, False])
    )

    # Rank entities per year
    df_sorted['Rank'] = df_sorted.groupby('Date')['Value'].rank(ascending=False, method='first')
    df_filtered = df_sorted[df_sorted['Rank'] <= top_n].copy()

    # Create Plotly Bar Race Chart
    fig = px.bar(
        df_filtered,
        x="Value",
        y="Entity",
        animation_frame="Date",
        animation_group="Entity",
        orientation="h",
        range_x=[0, df_filtered['Value'].max() * 1.1],
        title="Dynamic Bar Race Chart",
        color="Entity",
        text="Value"
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=600,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload a CSV file to generate the animated bar chart race.")