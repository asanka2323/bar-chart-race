import os
import io
import math
import requests
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import cv2
from moviepy import VideoClip

# ---------------------------------------------------------
# SETUP & CACHING FOR FONTS / ASSETS
# ---------------------------------------------------------
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. EASING & ANIMATION STYLES ENGINE
# ---------------------------------------------------------
def ease_linear(t):
    return t

def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

# ---------------------------------------------------------
# 2. HELPER FUNCTIONS & DRAWING UTILITIES
# ---------------------------------------------------------
def draw_rounded_rect(draw, xy, corner_radius, fill=None, outline=None, width=1):
    """Draws a rectangle with smooth rounded corners."""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + corner_radius, y1, x2 - corner_radius, y2], fill=fill)
    draw.rectangle([x1, y1 + corner_radius, x2, y2 - corner_radius], fill=fill)
    draw.pieslice([x1, y1, x1 + 2 * corner_radius, y1 + 2 * corner_radius], 180, 270, fill=fill)
    draw.pieslice([x2 - 2 * corner_radius, y1, x2, y1 + 2 * corner_radius], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2 * corner_radius, x1 + 2 * corner_radius, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2 * corner_radius, y2 - 2 * corner_radius, x2, y2], 0, 90, fill=fill)
    
    if outline:
        draw.arc([x1, y1, x1 + 2 * corner_radius, y1 + 2 * corner_radius], 180, 270, fill=outline, width=width)
        draw.arc([x2 - 2 * corner_radius, y1, x2, y1 + 2 * corner_radius], 270, 360, fill=outline, width=width)
        draw.arc([x1, y2 - 2 * corner_radius, x1 + 2 * corner_radius, y2], 90, 180, fill=outline, width=width)
        draw.arc([x2 - 2 * corner_radius, y2 - 2 * corner_radius, x2, y2], 0, 90, fill=outline, width=width)
        draw.line([x1 + corner_radius, y1, x2 - corner_radius, y1], fill=outline, width=width)
        draw.line([x1 + corner_radius, y2, x2 - corner_radius, y2], fill=outline, width=width)
        draw.line([x1, y1 + corner_radius, x1, y2 - corner_radius], fill=outline, width=width)
        draw.line([x2, y1 + corner_radius, x2, y2 - corner_radius], fill=outline, width=width)

# Color palettes for categories
CYBER_COLORS = [
    (0, 255, 153),   # Neon Mint
    (186, 85, 211),  # Medium Orchid
    (0, 191, 255),   # Deep Sky Blue
    (255, 191, 0),   # Amber
    (255, 0, 128),   # Neon Pink
    (127, 255, 0),   # Chartreuse
]

# ---------------------------------------------------------
# 3. FRAME RENDERER ENGINE
# ---------------------------------------------------------
def render_cyberpunk_frame(df_frame, year_label, frame_idx, style_key="cyber_pulse", width=1280, height=720):
    bg_color = (13, 17, 23)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Frame Dimensions
    top_margin = 120
    bottom_margin = 60
    left_margin = 250
    right_margin = 200
    
    chart_width = width - left_margin - right_margin
    chart_height = height - top_margin - bottom_margin

    # Title & Year Headers
    draw.rectangle([50, 40, 450, 95], outline=(0, 255, 153), width=2)
    draw.text((65, 48), "WORLD CAR MANUFACTURING", fill=(255, 255, 255))
    draw.text((65, 68), "TOP PRODUCERS • CYBERPUNK EDITION", fill=(0, 255, 153))

    # Big Year Display Box
    draw.rectangle([width - 350, 40, width - 50, 95], outline=(0, 255, 153), width=2)
    draw.text((width - 330, 52), f"YEAR:   {int(year_label)}", fill=(0, 255, 153))

    # Scale Values
    max_val = df_frame['Value'].max() if not df_frame.empty and df_frame['Value'].max() > 0 else 1
    top_n = min(10, len(df_frame))

    # Draw Bars
    if top_n > 0:
        bar_height = (chart_height / top_n) * 0.65
        bar_gap = (chart_height / top_n) * 0.35

        for i, (_, row) in enumerate(df_frame.head(top_n).iterrows()):
            cat_name = str(row['Category'])
            val = row['Value']

            y_pos = top_margin + i * (bar_height + bar_gap)
            bar_w = (val / max_val) * chart_width if max_val > 0 else 0

            color = CYBER_COLORS[i % len(CYBER_COLORS)]

            # Draw Label (Country Name)
            draw.text((left_margin - 150, y_pos + bar_height / 4), cat_name[:15], fill=(255, 255, 255))

            # Draw Bar
            if bar_w > 10:
                draw_rounded_rect(draw, [left_margin, y_pos, left_margin + bar_w, y_pos + bar_height], corner_radius=8, fill=color)

            # Draw Value Text
            val_str = f"{int(val):,}"
            draw.text((left_margin + bar_w + 15, y_pos + bar_height / 4), val_str, fill=color)

    return np.array(img)

# ---------------------------------------------------------
# 4. VIDEO ANIMATION ENGINE
# ---------------------------------------------------------
def generate_race_video(df, output_path="bar_chart_race.mp4", fps=30, seconds_per_year=2, default_style="cyber_pulse"):
    years = sorted(df['Date'].unique())
    categories = df['Category'].unique()

    frames_per_year = fps * seconds_per_year
    total_frames = (len(years) - 1) * frames_per_year

    interp_records = []

    for i in range(len(years) - 1):
        y0, y1 = years[i], years[i+1]
        df0 = df[df['Date'] == y0].set_index('Category')
        df1 = df[df['Date'] == y1].set_index('Category')

        for f in range(frames_per_year):
            frame_idx = i * frames_per_year + f
            t = f / float(frames_per_year)
            t_eased = ease_in_out_cubic(t)

            year_interp = y0 + (y1 - y0) * t

            for cat in categories:
                v0 = df0.loc[cat, 'Value'] if cat in df0.index else 0
                v1 = df1.loc[cat, 'Value'] if cat in df1.index else 0
                v_interp = v0 + (v1 - v0) * t_eased

                interp_records.append({
                    'Frame': frame_idx,
                    'YearLabel': year_interp,
                    'Category': cat,
                    'Value': v_interp,
                    'Style': default_style
                })

    df_interp = pd.DataFrame(interp_records)
    max_frame = df_interp['Frame'].max() if not df_interp.empty else 0

    def make_frame(t):
        frame_idx = int(t * fps)
        frame_idx = min(frame_idx, max_frame)

        sub_df = df_interp[df_interp['Frame'] == frame_idx].sort_values(by='Value', ascending=False)
        year_lbl = sub_df['YearLabel'].iloc[0] if not sub_df.empty else years[0]
        style_used = sub_df['Style'].iloc[0] if not sub_df.empty else default_style
        return render_cyberpunk_frame(sub_df, year_label=year_lbl, frame_idx=frame_idx, style_key=style_used)

    duration = total_frames / fps
    clip = VideoClip(make_frame, duration=duration)
    clip.write_videofile(output_path, fps=fps, codec='libx264', audio=False)

# ---------------------------------------------------------
# 5. STREAMLIT APPLICATION INTERFACE
# ---------------------------------------------------------
if __name__ == "__main__":
    st.set_page_config(page_title="Cyberpunk Bar Chart Race", layout="wide")
    st.title("Cyberpunk Bar Chart Race Generator")

    # CSV File Uploader
    uploaded_file = st.file_uploader("Upload your dataset (CSV)", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        # Reshape wide-format datasets (e.g., Country, Flag, 1990, 1991...) to long-format
        if 'Date' not in df.columns or 'Category' not in df.columns or 'Value' not in df.columns:
            id_vars = [col for col in df.columns if not str(col).isdigit()]
            value_vars = [col for col in df.columns if str(col).isdigit()]

            cat_col = 'Country' if 'Country' in id_vars else (id_vars[0] if id_vars else df.columns[0])

            df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='Date', value_name='Value')
            df = df.rename(columns={cat_col: 'Category'})
            df['Date'] = pd.to_numeric(df['Date'], errors='coerce')
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce').fillna(0)

        st.write("### Dataset Preview", df.head())

        if st.button("Generate Cyberpunk Video"):
            with st.spinner("Generating video... Please wait a moment."):
                generate_race_video(df, output_path="bar_chart_race.mp4", default_style="cyber_pulse")

            st.success("Video generated successfully!")

            with open("bar_chart_race.mp4", "rb") as video_file:
                video_bytes = video_file.read()
            st.video(video_bytes)
    else:
        st.info("Please upload a CSV file to generate the video.")