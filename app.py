import os
import io
import math
import requests
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoClip

# ---------------------------------------------------------
# CACHE DIRECTORY FOR IMAGES / FLAGS
# ---------------------------------------------------------
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

IMAGE_CACHE = {}

def get_image(url_or_path):
    """Downloads or loads an image and caches it in memory."""
    if not url_or_path or pd.isna(url_or_path) or str(url_or_path).strip() == "":
        return None
    
    url_str = str(url_or_path).strip()
    if url_str in IMAGE_CACHE:
        return IMAGE_CACHE[url_str]
    
    try:
        if url_str.startswith("http://") or url_str.startswith("https://"):
            response = requests.get(url_str, timeout=5)
            img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        elif os.path.exists(url_str):
            img = Image.open(url_str).convert("RGBA")
        else:
            return None
        
        # Crop/Resize to square
        w, h = img.size
        min_dim = min(w, h)
        img_cropped = img.crop(((w - min_dim) // 2, (h - min_dim) // 2, (w + min_dim) // 2, (h + min_dim) // 2))
        IMAGE_CACHE[url_str] = img_cropped
        return img_cropped
    except Exception:
        return None

# ---------------------------------------------------------
# EASING FUNCTIONS
# ---------------------------------------------------------
def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

def draw_rounded_rect(draw, xy, corner_radius, fill=None, outline=None, width=1):
    x1, y1, x2, y2 = xy
    if x2 - x1 < corner_radius * 2:
        corner_radius = max(1, (x2 - x1) / 2)
    draw.rectangle([x1 + corner_radius, y1, x2 - corner_radius, y2], fill=fill)
    draw.rectangle([x1, y1 + corner_radius, x2, y2 - corner_radius], fill=fill)
    draw.pieslice([x1, y1, x1 + 2 * corner_radius, y1 + 2 * corner_radius], 180, 270, fill=fill)
    draw.pieslice([x2 - 2 * corner_radius, y1, x2, y1 + 2 * corner_radius], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2 * corner_radius, x1 + 2 * corner_radius, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2 * corner_radius, y2 - 2 * corner_radius, x2, y2], 0, 90, fill=fill)

# Default Cyberpunk Palette
DEFAULT_PALETTE = [
    "#00FF99", "#BA55D3", "#00BFFF", "#FFBF00", "#FF0080",
    "#7FFF00", "#FF4500", "#00EEEE", "#FFD700", "#FF1493"
]

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

# ---------------------------------------------------------
# VERTICAL FRAME RENDERER (1080 x 1920)
# ---------------------------------------------------------
def render_cyberpunk_frame(df_frame, year_label, color_map, title="BAR CHART RACE", subtitle="CYBERPUNK EDITION", width=1080, height=1920):
    bg_color = (13, 17, 23)
    img = Image.new("RGBA", (width, height), bg_color + (255,))
    draw = ImageDraw.Draw(img)

    top_margin = 280
    bottom_margin = 120
    left_margin = 320
    right_margin = 180
    
    chart_width = width - left_margin - right_margin
    chart_height = height - top_margin - bottom_margin

    # Top Banner Header
    draw.rectangle([60, 80, width - 60, 200], outline=(0, 255, 153), width=3)
    draw.text((90, 100), str(title).upper(), fill=(255, 255, 255))
    draw.text((90, 140), str(subtitle).upper(), fill=(0, 255, 153))

    # Large Year Watermark / Card
    draw.rectangle([width - 380, 110, width - 90, 170], outline=(0, 255, 153), width=2)
    draw.text((width - 360, 125), f"YEAR: {int(year_label)}", fill=(0, 255, 153))

    max_val = df_frame['Value'].max() if not df_frame.empty and df_frame['Value'].max() > 0 else 1
    top_n = 10

    bar_height = (chart_height / top_n) * 0.60
    bar_gap = (chart_height / top_n) * 0.40

    for _, row in df_frame.iterrows():
        cat_name = str(row['Category'])
        val = row['Value']
        rank = row['Rank']
        flag_url = row.get('Flag', None)

        # Skip bars that drift out of top 10 bounds
        if rank > top_n + 0.5:
            continue

        y_pos = top_margin + rank * (bar_height + bar_gap)
        bar_w = (val / max_val) * chart_width if max_val > 0 else 0

        color_hex = color_map.get(cat_name, "#00FF99")
        color_rgb = hex_to_rgb(color_hex)

        # 1. Render Icon / Flag / Logo Image
        icon_img = get_image(flag_url)
        icon_size = int(bar_height * 1.1)
        if icon_img:
            icon_resized = icon_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            img.paste(icon_resized, (left_margin - icon_size - 20, int(y_pos - (icon_size - bar_height) / 2)), icon_resized)

        # 2. Render Text Label (Entity Name)
        draw.text((60, y_pos + bar_height / 4), cat_name[:16], fill=(255, 255, 255))

        # 3. Render Rounded Horizontal Bar
        if bar_w > 10:
            draw_rounded_rect(draw, [left_margin, y_pos, left_margin + bar_w, y_pos + bar_height], corner_radius=12, fill=color_rgb)

        # 4. Render Metric Value
        val_str = f"{int(val):,}"
        draw.text((left_margin + bar_w + 20, y_pos + bar_height / 4), val_str, fill=color_rgb)

    return np.array(img.convert("RGB"))

# ---------------------------------------------------------
# VIDEO GENERATION ENGINE WITH SMOOTH SHIFTING
# ---------------------------------------------------------
def generate_race_video(df, color_map, title, subtitle, output_path="bar_chart_race.mp4", fps=30, seconds_per_year=2):
    years = sorted(df['Date'].unique())
    categories = df['Category'].unique()

    frames_per_year = fps * seconds_per_year
    total_frames = (len(years) - 1) * frames_per_year

    interp_records = []

    for i in range(len(years) - 1):
        y0, y1 = years[i], years[i+1]
        
        df0 = df[df['Date'] == y0].sort_values(by='Value', ascending=False).reset_index(drop=True)
        df1 = df[df['Date'] == y1].sort_values(by='Value', ascending=False).reset_index(drop=True)

        df0['Rank0'] = df0.index
        df1['Rank1'] = df1.index

        df0_map = df0.set_index('Category')
        df1_map = df1.set_index('Category')

        for f in range(frames_per_year):
            frame_idx = i * frames_per_year + f
            t = f / float(frames_per_year)
            t_eased = ease_in_out_cubic(t)

            year_interp = y0 + (y1 - y0) * t

            for cat in categories:
                v0 = df0_map.loc[cat, 'Value'] if cat in df0_map.index else 0
                v1 = df1_map.loc[cat, 'Value'] if cat in df1_map.index else 0
                r0 = df0_map.loc[cat, 'Rank0'] if cat in df0_map.index else 15
                r1 = df1_map.loc[cat, 'Rank1'] if cat in df1_map.index else 15

                flag_val = df0_map.loc[cat, 'Flag'] if (cat in df0_map.index and 'Flag' in df0_map.columns) else None

                v_interp = v0 + (v1 - v0) * t_eased
                r_interp = r0 + (r1 - r0) * t_eased

                interp_records.append({
                    'Frame': frame_idx,
                    'YearLabel': year_interp,
                    'Category': cat,
                    'Value': v_interp,
                    'Rank': r_interp,
                    'Flag': flag_val
                })

    df_interp = pd.DataFrame(interp_records)
    max_frame = df_interp['Frame'].max() if not df_interp.empty else 0

    def make_frame(t):
        frame_idx = int(t * fps)
        frame_idx = min(frame_idx, max_frame)

        sub_df = df_interp[df_interp['Frame'] == frame_idx]
        year_lbl = sub_df['YearLabel'].iloc[0] if not sub_df.empty else years[0]
        
        return render_cyberpunk_frame(sub_df, year_label=year_lbl, color_map=color_map, title=title, subtitle=subtitle)

    duration = total_frames / fps
    clip = VideoClip(make_frame, duration=duration)
    clip.write_videofile(output_path, fps=fps, codec='libx264', audio=False)

# ---------------------------------------------------------
# STREAMLIT USER INTERFACE
# ---------------------------------------------------------
if __name__ == "__main__":
    st.set_page_config(page_title="Cyberpunk Bar Chart Race", layout="wide")
    st.title("Vertical Cyberpunk Bar Chart Race Generator")

    uploaded_file = st.file_uploader("Upload Dataset (CSV)", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        # Auto-reshape Wide Datasets (Country, Flag, 1990, 1991...) to Long Format
        if 'Date' not in df.columns or 'Category' not in df.columns or 'Value' not in df.columns:
            id_vars = [col for col in df.columns if not str(col).isdigit()]
            value_vars = [col for col in df.columns if str(col).isdigit()]

            cat_col = 'Country' if 'Country' in id_vars else (id_vars[0] if id_vars else df.columns[0])

            df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='Date', value_name='Value')
            df = df.rename(columns={cat_col: 'Category'})
            df['Date'] = pd.to_numeric(df['Date'], errors='coerce')
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce').fillna(0)

        st.write("### Dataset Preview", df.head())

        # Header Titles Customization
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            title_input = st.text_input("Main Title", value="WORLD CAR MANUFACTURING")
        with col_t2:
            subtitle_input = st.text_input("Subtitle", value="TOP PRODUCERS • CYBERPUNK EDITION")

        # Dynamic Entity Color Customization
        st.write("### Custom Entity Colors")
        unique_entities = sorted(df['Category'].unique())
        color_map = {}

        cols = st.columns(4)
        for idx, entity in enumerate(unique_entities):
            default_hex = DEFAULT_PALETTE[idx % len(DEFAULT_PALETTE)]
            with cols[idx % 4]:
                color_map[entity] = st.color_picker(f"Color: {entity}", value=default_hex)

        if st.button("Generate Vertical Cyberpunk Video"):
            with st.spinner("Rendering vertical video with smooth rank shifting and icons..."):
                generate_race_video(
                    df,
                    color_map=color_map,
                    title=title_input,
                    subtitle=subtitle_input,
                    output_path="bar_chart_race.mp4"
                )

            st.success("Video generated successfully!")

            with open("bar_chart_race.mp4", "rb") as video_file:
                video_bytes = video_file.read()
            st.video(video_bytes)
    else:
        st.info("Upload a CSV file to customize colors, titles, and render your vertical bar chart race video.")