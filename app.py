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
# COUNTRY ISO MAP FOR AUTO-FLAG LOOKUP
# ---------------------------------------------------------
COUNTRY_ISO_MAP = {
    "united states": "us", "usa": "us", "japan": "jp", "germany": "de",
    "france": "fr", "spain": "es", "south korea": "kr", "china": "cn",
    "mexico": "mx", "brazil": "br", "malaysia": "my", "indonesia": "id",
    "italy": "it", "united kingdom": "gb", "uk": "gb", "canada": "ca",
    "india": "in", "russia": "ru", "russian federation": "ru",
    "poland": "pl", "portugal": "pt", "romania": "ro", "slovakia": "sk",
    "south africa": "za", "sweden": "se", "thailand": "th", "turkey": "tr",
    "uzbekistan": "uz"
}

def get_flag_url(category_name, given_flag_url=None):
    if given_flag_url and pd.notna(given_flag_url) and str(given_flag_url).strip() != "":
        url_str = str(given_flag_url).strip()
        if "wikimedia.org" in url_str and url_str.endswith(".svg") and "?width=" not in url_str:
            url_str += "?width=200"
        return url_str

    clean_name = str(category_name).strip().lower()
    iso = COUNTRY_ISO_MAP.get(clean_name)
    if iso:
        return f"https://flagcdn.com/w160/{iso}.png"
    return None

def load_circular_image(url_or_path):
    if not url_or_path or pd.isna(url_or_path) or str(url_or_path).strip() == "":
        return None
    url_str = str(url_or_path).strip()
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        if url_str.startswith("http://") or url_str.startswith("https://"):
            res = requests.get(url_str, headers=headers, timeout=5)
            if res.status_code == 200:
                img = Image.open(io.BytesIO(res.content)).convert("RGBA")
            else:
                return None
        elif os.path.exists(url_str):
            img = Image.open(url_str).convert("RGBA")
        else:
            return None
        
        w, h = img.size
        min_dim = min(w, h)
        img_cropped = img.crop(((w - min_dim) // 2, (h - min_dim) // 2, (w + min_dim) // 2, (h + min_dim) // 2))
        
        mask = Image.new('L', (min_dim, min_dim), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, min_dim, min_dim), fill=255)
        
        circular_img = Image.new('RGBA', (min_dim, min_dim), (0, 0, 0, 0))
        circular_img.paste(img_cropped, (0, 0), mask=mask)
        return circular_img
    except Exception:
        return None

def fetch_all_flags(df):
    flag_dict = {}
    categories = df['Category'].unique()
    for cat in categories:
        given_flag = None
        if 'Flag' in df.columns:
            sub = df[df['Category'] == cat]
            if not sub.empty:
                given_flag = sub['Flag'].iloc[0]
        url = get_flag_url(cat, given_flag)
        if url:
            img = load_circular_image(url)
            if img:
                flag_dict[cat] = img
    return flag_dict

# ---------------------------------------------------------
# DRAWING & FONT UTILITIES
# ---------------------------------------------------------
def load_font(size, bold=False):
    font_names = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial.ttf",
        "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"
    ]
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()

def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

def draw_rounded_rect(draw, xy, corner_radius, fill=None):
    x1, y1, x2, y2 = xy
    if x2 - x1 < corner_radius * 2:
        corner_radius = max(1, (x2 - x1) / 2)
    draw.rectangle([x1 + corner_radius, y1, x2 - corner_radius, y2], fill=fill)
    draw.rectangle([x1, y1 + corner_radius, x2, y2 - corner_radius], fill=fill)
    draw.pieslice([x1, y1, x1 + 2 * corner_radius, y1 + 2 * corner_radius], 180, 270, fill=fill)
    draw.pieslice([x2 - 2 * corner_radius, y1, x2, y1 + 2 * corner_radius], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2 * corner_radius, x1 + 2 * corner_radius, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2 * corner_radius, y2 - 2 * corner_radius, x2, y2], 0, 90, fill=fill)

DEFAULT_PALETTE = [
    "#FFD700", "#00BFFF", "#00EEEE", "#FF4500", "#FF0080",
    "#BA55D3", "#7FFF00", "#00FF99", "#FFBF00", "#FF1493"
]

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

# ---------------------------------------------------------
# FRAME RENDERER (LARGER FONTS & PERFECT ALIGNMENT)
# ---------------------------------------------------------
def render_cyberpunk_frame(df_frame, year_label, color_map, loaded_flags, title="BAR CHART RACE", subtitle="CYBERPUNK EDITION", width=720, height=1280):
    bg_color = (13, 17, 23)
    img = Image.new("RGBA", (width, height), bg_color + (255,))
    draw = ImageDraw.Draw(img)

    # Pre-load custom fonts at larger sizes
    font_title = load_font(24, bold=True)
    font_subtitle = load_font(18, bold=True)
    font_label = load_font(18, bold=True)
    font_value = load_font(18, bold=True)
    font_year = load_font(22, bold=True)

    top_margin = 180
    bottom_margin = 80
    
    # Layout spacing coordinates
    label_right_align = 125  # End of country name label
    flag_x = 135             # Flag icon start
    left_margin = 200        # Animated bar start
    right_margin = 110       # Right margin for numbers
    
    chart_width = width - left_margin - right_margin
    chart_height = height - top_margin - bottom_margin

    # Header Card
    draw.rectangle([20, 35, width - 20, 145], outline=(0, 255, 153), width=2)
    draw.text((40, 50), str(title).upper(), font=font_title, fill=(255, 255, 255))
    draw.text((40, 95), str(subtitle).upper(), font=font_subtitle, fill=(0, 255, 153))

    # Year Display Card
    draw.rectangle([width - 240, 55, width - 40, 125], outline=(0, 255, 153), width=2)
    draw.text((width - 220, 75), f"YEAR: {int(year_label)}", font=font_year, fill=(0, 255, 153))

    max_val = df_frame['Value'].max() if not df_frame.empty and df_frame['Value'].max() > 0 else 1
    top_n = 10

    bar_height = (chart_height / top_n) * 0.60
    bar_gap = (chart_height / top_n) * 0.40

    for _, row in df_frame.iterrows():
        cat_name = str(row['Category'])
        val = row['Value']
        rank = row['Rank']

        if rank > top_n + 0.5:
            continue

        y_pos = top_margin + rank * (bar_height + bar_gap)
        bar_w = (val / max_val) * chart_width if max_val > 0 else 0

        color_hex = color_map.get(cat_name, "#00FF99")
        color_rgb = hex_to_rgb(color_hex)

        # 1. Text Label (Right-aligned with larger font size)
        label_text = cat_name[:12]
        bbox = draw.textbbox((0, 0), label_text, font=font_label)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = label_right_align - text_w
        text_y = y_pos + (bar_height - text_h) / 2 - 2
        draw.text((max(10, text_x), text_y), label_text, font=font_label, fill=(255, 255, 255))

        # 2. Flag Image Placement
        icon_img = loaded_flags.get(cat_name)
        icon_size = int(bar_height * 0.95)
        icon_y = int(y_pos + (bar_height - icon_size) / 2)

        if icon_img:
            icon_resized = icon_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            img.paste(icon_resized, (flag_x, icon_y), icon_resized)
        else:
            # Fallback Circle with Initials
            draw.ellipse([flag_x, icon_y, flag_x + icon_size, icon_y + icon_size], outline=color_rgb, width=2)
            initials = cat_name[:2].upper()
            draw.text((flag_x + int(icon_size / 4), icon_y + int(icon_size / 4)), initials, font=font_label, fill=(255, 255, 255))

        # 3. Bar
        if bar_w > 5:
            draw_rounded_rect(draw, [left_margin, y_pos, left_margin + bar_w, y_pos + bar_height], corner_radius=8, fill=color_rgb)

        # 4. Value Text (Larger font size)
        val_str = f"{int(val):,}"
        val_bbox = draw.textbbox((0, 0), val_str, font=font_value)
        val_h = val_bbox[3] - val_bbox[1]
        val_y = y_pos + (bar_height - val_h) / 2 - 2
        draw.text((left_margin + bar_w + 10, val_y), val_str, font=font_value, fill=color_rgb)

    return np.array(img.convert("RGB"))

# ---------------------------------------------------------
# FAST VIDEO GENERATION ENGINE
# ---------------------------------------------------------
def generate_race_video(df, color_map, title, subtitle, output_path="bar_chart_race.mp4", fps=20, seconds_per_year=1.0):
    loaded_flags = fetch_all_flags(df)

    years = sorted(df['Date'].unique())
    categories = df['Category'].unique()

    frames_per_year = int(fps * seconds_per_year)
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

                v_interp = v0 + (v1 - v0) * t_eased
                r_interp = r0 + (r1 - r0) * t_eased

                interp_records.append({
                    'Frame': frame_idx,
                    'YearLabel': year_interp,
                    'Category': cat,
                    'Value': v_interp,
                    'Rank': r_interp
                })

    df_interp = pd.DataFrame(interp_records)
    max_frame = df_interp['Frame'].max() if not df_interp.empty else 0

    def make_frame(t):
        frame_idx = int(t * fps)
        frame_idx = min(frame_idx, max_frame)

        sub_df = df_interp[df_interp['Frame'] == frame_idx]
        year_lbl = sub_df['YearLabel'].iloc[0] if not sub_df.empty else years[0]
        
        return render_cyberpunk_frame(sub_df, year_label=year_lbl, color_map=color_map, loaded_flags=loaded_flags, title=title, subtitle=subtitle)

    duration = total_frames / fps
    clip = VideoClip(make_frame, duration=duration)
    
    clip.write_videofile(
        output_path,
        fps=fps,
        codec='libx264',
        audio=False,
        preset='ultrafast',
        threads=4,
        logger=None
    )

# ---------------------------------------------------------
# STREAMLIT UI
# ---------------------------------------------------------
if __name__ == "__main__":
    st.set_page_config(page_title="Vertical Bar Chart Race", layout="wide")
    st.title("Vertical Cyberpunk Bar Chart Race Generator")

    uploaded_file = st.file_uploader("Upload Dataset (CSV)", type=["csv"])

    if uploaded_file is not None:
        if 'df' not in st.session_state or st.session_state.get('uploaded_filename') != uploaded_file.name:
            df = pd.read_csv(uploaded_file)

            if 'Date' not in df.columns or 'Category' not in df.columns or 'Value' not in df.columns:
                id_vars = [col for col in df.columns if not str(col).isdigit()]
                value_vars = [col for col in df.columns if str(col).isdigit()]

                cat_col = 'Country' if 'Country' in id_vars else (id_vars[0] if id_vars else df.columns[0])

                df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='Date', value_name='Value')
                df = df.rename(columns={cat_col: 'Category'})
                df['Date'] = pd.to_numeric(df['Date'], errors='coerce')
                df['Value'] = pd.to_numeric(df['Value'], errors='coerce').fillna(0)

            st.session_state['df'] = df
            st.session_state['uploaded_filename'] = uploaded_file.name
        else:
            df = st.session_state['df']

        st.write("### Dataset Preview", df.head())

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            title_input = st.text_input("Main Title", value="WORLD CAR MANUFACTURING")
        with col_t2:
            subtitle_input = st.text_input("Subtitle", value="TOP PRODUCERS • CYBERPUNK EDITION")

        st.write("### Custom Entity Colors")
        unique_entities = sorted(df['Category'].unique())
        color_map = {}

        cols = st.columns(4)
        for idx, entity in enumerate(unique_entities):
            default_hex = DEFAULT_PALETTE[idx % len(DEFAULT_PALETTE)]
            with cols[idx % 4]:
                color_map[entity] = st.color_picker(f"Color: {entity}", value=default_hex, key=f"cp_{entity}")

        if st.button("Generate Vertical Cyberpunk Video"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Pre-downloading flags & rendering frames...")
            progress_bar.progress(30)
            
            output_path = "bar_chart_race.mp4"
            generate_race_video(
                df,
                color_map=color_map,
                title=title_input,
                subtitle=subtitle_input,
                output_path=output_path,
                fps=20,
                seconds_per_year=1.0
            )
            
            progress_bar.progress(100)
            status_text.text("Rendering complete!")

            with open(output_path, "rb") as vf:
                st.session_state['video_bytes'] = vf.read()

            st.success("Video generated successfully!")

        if 'video_bytes' in st.session_state:
            st.video(st.session_state['video_bytes'])
    else:
        st.info("Upload a CSV file to customize colors, titles, and render your video.")