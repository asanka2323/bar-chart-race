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
# THEME & COLOR PALETTE
# ---------------------------------------------------------
THEMES = {
    "Light Mode (Default)": {
        "bg_color": (245, 244, 238),       # #F5F4EE Warm Poster Background
        "title_color": (18, 30, 66),       # #121E42 Deep Navy Title
        "subtitle_color": (18, 30, 66),    # #121E42 Deep Navy Subtitle
        "grid_color": (218, 216, 206),     # Grid lines
        "label_color": (18, 30, 66),      # Dark text for country names
        "value_color": (18, 30, 66),      # Dark text for numbers
        "year_color": (18, 30, 66),       # Deep Navy Year Number
        "bar_primary": "#121E42",
        "bar_stroke": False
    },
    "Dark Mode (Shorts)": {
        "bg_color": (15, 23, 42),         # #0F172A Deep Navy
        "title_color": (249, 250, 251),    # White Title
        "subtitle_color": (209, 213, 219), # Gray Subtitle
        "grid_color": (30, 41, 59),       # Grid lines
        "label_color": (249, 250, 251),   # White Country Names
        "value_color": (249, 250, 251),   # White Values
        "year_color": (249, 250, 251),    # White Year
        "bar_primary": "#1E3A8A",
        "bar_stroke": True
    }
}

DEFAULT_ACCENT_COLORS = [
    "#121E42", "#2B4C7E", "#0A6640", "#B22222", "#004B87",
    "#D85A27", "#1E3A8A", "#059669", "#7C3AED", "#9333EA"
]

COUNTRY_ISO_MAP = {
    "united states": "us", "usa": "us", "japan": "jp", "germany": "de",
    "france": "fr", "spain": "es", "south korea": "kr", "china": "cn",
    "mexico": "mx", "brazil": "br", "malaysia": "my", "indonesia": "id",
    "italy": "it", "united kingdom": "gb", "uk": "gb", "canada": "ca",
    "india": "in", "russia": "ru", "poland": "pl", "texas": "us-tx", "california": "us-ca"
}

# ---------------------------------------------------------
# FONT HELPER
# ---------------------------------------------------------
def load_brand_font(family="Montserrat", variant="Bold", size=20):
    font_files = [
        f"fonts/{family}-{variant}.ttf",
        f"{family}-{variant}.ttf",
        "DejaVuSans-Bold.ttf" if "Bold" in variant else "DejaVuSans.ttf",
        "Arial.ttf"
    ]
    for font_path in font_files:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue
    return ImageFont.load_default()

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

# ---------------------------------------------------------
# FLAG & ICON HELPERS
# ---------------------------------------------------------
def get_flag_url(category_name, given_flag_url=None):
    if given_flag_url and pd.notna(given_flag_url) and str(given_flag_url).strip() != "":
        url_str = str(given_flag_url).strip()
        if "wikimedia.org" in url_str and url_str.endswith(".svg") and "?width=" not in url_str:
            url_str += "?width=200"
        return url_str

    clean_name = str(category_name).strip().lower()
    iso = COUNTRY_ISO_MAP.get(clean_name)
    if iso and not iso.startswith("us-"):
        return f"https://flagcdn.com/w160/{iso}.png"
    return None

def load_circular_image(url_or_path):
    if not url_or_path or pd.isna(url_or_path) or str(url_or_path).strip() == "":
        return None
    url_str = str(url_or_path).strip()
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
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
    for cat in df['Category'].unique():
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
# FRAME RENDERER (EXACT POSTER LOOK)
# ---------------------------------------------------------
def render_brand_frame(df_frame, year_label, color_map, loaded_flags, theme_config, title="STATE GDP\nGROWTH", subtitle="MEASURED IN CURRENT MILLIONS", width=720, height=1280):
    bg_color = theme_config["bg_color"]
    img = Image.new("RGBA", (width, height), bg_color + (255,))
    draw = ImageDraw.Draw(img)

    # Large Fonts matching poster layout
    font_main_title = load_brand_font("Montserrat", "ExtraBold", 62)
    font_subtitle = load_brand_font("Montserrat", "Bold", 28)
    font_big_year = load_brand_font("Montserrat", "ExtraBold", 140)
    font_label = load_brand_font("Inter", "Bold", 22)
    font_value = load_brand_font("Montserrat", "Bold", 22)

    top_margin = 290
    bottom_margin = 150
    label_right_align = 145
    flag_x = 155
    left_margin = 220
    right_margin = 100

    chart_width = width - left_margin - right_margin
    chart_height = height - top_margin - bottom_margin

    # 1. Background Grid Lines
    grid_color = theme_config["grid_color"]
    for i in range(5):
        gx = left_margin + (chart_width / 4) * i
        draw.line([(gx, top_margin - 10), (gx, height - bottom_margin)], fill=grid_color, width=2)

    # 2. Main Title (Big, ExtraBold Upper Left)
    title_lines = str(title).strip().upper().split('\n')
    y_title_offset = 40
    for line in title_lines:
        draw.text((40, y_title_offset), line, font=font_main_title, fill=theme_config["title_color"])
        bbox = draw.textbbox((0, 0), line, font=font_main_title)
        y_title_offset += (bbox[3] - bbox[1]) + 6

    # 3. Subtitle (Directly below Title)
    draw.text((40, y_title_offset + 10), str(subtitle).strip().upper(), font=font_subtitle, fill=theme_config["subtitle_color"])

    max_val = df_frame['Value'].max() if not df_frame.empty and df_frame['Value'].max() > 0 else 1
    top_n = 10

    bar_height = (chart_height / top_n) * 0.58
    bar_gap = (chart_height / top_n) * 0.42

    for _, row in df_frame.iterrows():
        cat_name = str(row['Category'])
        val = row['Value']
        rank = row['Rank']

        if rank > top_n + 0.5:
            continue

        y_pos = top_margin + rank * (bar_height + bar_gap)
        bar_w = (val / max_val) * chart_width if max_val > 0 else 0

        color_hex = color_map.get(cat_name, theme_config["bar_primary"])
        color_rgb = hex_to_rgb(color_hex)

        # Entity Label
        label_text = cat_name[:12]
        bbox = draw.textbbox((0, 0), label_text, font=font_label)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text((max(10, label_right_align - text_w), y_pos + (bar_height - text_h) / 2 - 2), label_text, font=font_label, fill=theme_config["label_color"])

        # Flag Icon
        icon_img = loaded_flags.get(cat_name)
        icon_size = int(bar_height * 0.95)
        icon_y = int(y_pos + (bar_height - icon_size) / 2)

        if icon_img:
            icon_resized = icon_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            img.paste(icon_resized, (flag_x, icon_y), icon_resized)
        else:
            draw.ellipse([flag_x, icon_y, flag_x + icon_size, icon_y + icon_size], fill=color_rgb)
            initials = cat_name[:2].upper()
            draw.text((flag_x + int(icon_size / 4), icon_y + int(icon_size / 4)), initials, font=font_label, fill=(255, 255, 255))

        # Bar
        if bar_w > 5:
            bar_rect = [left_margin, y_pos, left_margin + bar_w, y_pos + bar_height]
            draw.rounded_rectangle(bar_rect, radius=4, fill=color_rgb)
            if theme_config["bar_stroke"]:
                draw.rounded_rectangle(bar_rect, radius=4, outline=(255, 255, 255), width=2)

        # Value Text
        val_str = f"{int(val):,}"
        val_bbox = draw.textbbox((0, 0), val_str, font=font_value)
        val_h = val_bbox[3] - val_bbox[1]
        draw.text((left_margin + bar_w + 10, y_pos + (bar_height - val_h) / 2 - 2), val_str, font=font_value, fill=theme_config["value_color"])

    # 4. Big Bold Bottom-Right Year Display
    year_str = f"{int(year_label)}"
    bbox_year = draw.textbbox((0, 0), year_str, font=font_big_year)
    year_w = bbox_year[2] - bbox_year[0]
    year_h = bbox_year[3] - bbox_year[1]
    
    draw.text((width - year_w - 40, height - year_h - 60), year_str, font=font_big_year, fill=theme_config["year_color"])

    return np.array(img.convert("RGB"))

# ---------------------------------------------------------
# VIDEO ENGINE
# ---------------------------------------------------------
def generate_brand_race_video(df, color_map, title, subtitle, theme_choice, output_path="statrise_race.mp4", fps=20, seconds_per_year=1.0):
    theme_config = THEMES[theme_choice]
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
        
        return render_brand_frame(sub_df, year_label=year_lbl, color_map=color_map, loaded_flags=loaded_flags, theme_config=theme_config, title=title, subtitle=subtitle)

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
# STREAMLIT USER INTERFACE
# ---------------------------------------------------------
if __name__ == "__main__":
    st.set_page_config(page_title="StatRise Race Studio", layout="wide")
    st.title("StatRise Studio • Chart Race Video Generator")

    with st.sidebar:
        st.header("Display Theme")
        theme_choice = st.radio("Select Theme Mode", list(THEMES.keys()), index=0)

    st.write("### 1. Video Customization")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        title_input = st.text_area("Main Video Title (Use Enter for new lines)", value="STATE GDP\nGROWTH", height=90)
    with col_t2:
        subtitle_input = st.text_input("Subtitle / Unit Measurement", value="MEASURED IN CURRENT MILLIONS")

    st.write("### 2. Dataset Upload")
    uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])

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

        st.write("### 3. Custom Bar Colors")
        unique_entities = sorted(df['Category'].unique())
        color_map = {}

        cols = st.columns(4)
        for idx, entity in enumerate(unique_entities):
            default_hex = DEFAULT_ACCENT_COLORS[idx % len(DEFAULT_ACCENT_COLORS)]
            with cols[idx % 4]:
                color_map[entity] = st.color_picker(f"Color: {entity}", value=default_hex, key=f"cp_{entity}")

        if st.button("Generate Video"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Rendering video frames...")
            progress_bar.progress(30)
            
            output_path = "statrise_race.mp4"
            generate_brand_race_video(
                df,
                color_map=color_map,
                title=title_input,
                subtitle=subtitle_input,
                theme_choice=theme_choice,
                output_path=output_path,
                fps=20,
                seconds_per_year=1.0
            )
            
            progress_bar.progress(100)
            status_text.text("Rendering complete!")

            with open(output_path, "rb") as vf:
                st.session_state['video_bytes'] = vf.read()

            st.success("Chart race video generated successfully!")

        if 'video_bytes' in st.session_state:
            st.video(st.session_state['video_bytes'])
    else:
        st.info("Upload a CSV file above to set colors and render your chart race video.")