import os
import requests
import io
import cv2
import math
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from moviepy.video.VideoClip import VideoClip

# ---------------------------------------------------------
# 1. EASING & ANIMATION STYLES ENGINE
# ---------------------------------------------------------
def ease_linear(t):
    return t

def ease_in_out_quad(t):
    return 2 * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 2) / 2

def ease_out_bounce(t):
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375

def ease_out_elastic(t):
    if t == 0 or t == 1:
        return t
    return math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1

ANIMATION_STYLES = {
    'linear': {
        'easing': ease_linear,
        'pulse_glow': False,
        'label': 'Linear Continuous'
    },
    'smooth': {
        'easing': ease_in_out_quad,
        'pulse_glow': False,
        'label': 'Smooth Acceleration'
    },
    'cyber_pulse': {
        'easing': ease_in_out_quad,
        'pulse_glow': True,
        'label': 'Cyberpunk Neon Pulse'
    },
    'elastic_pop': {
        'easing': ease_out_elastic,
        'pulse_glow': True,
        'label': 'Elastic / Overshoot'
    },
    'bounce': {
        'easing': ease_out_bounce,
        'pulse_glow': False,
        'label': 'Bouncy Step'
    }
}

# ---------------------------------------------------------
# 2. CONFIGURATION & HELPERS
# ---------------------------------------------------------
FONT_PATH = "Fonts/Barlow-Bold.ttf"
CSV_PATH = "sample_data.csv"
CACHE_DIR = "cache"

os.makedirs(CACHE_DIR, exist_ok=True)

def get_font(size):
    if os.path.exists(FONT_PATH):
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()

def hex_to_rgb(hex_str):
    if not isinstance(hex_str, str) or not hex_str.startswith("#"):
        return (0, 229, 255)
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return (0, 229, 255)

def derive_color_profile(hex_str):
    main_rgb = hex_to_rgb(hex_str)
    glow_rgb = tuple(min(255, int(c * 1.15)) for c in main_rgb)
    dark_rgb = tuple(max(5, int(c * 0.15)) for c in main_rgb)
    return {'main': main_rgb, 'glow': glow_rgb, 'dark': dark_rgb}

def sanitize_url(url):
    if isinstance(url, str) and "upload.wikimedia.org" in url and url.endswith(".svg"):
        parts = url.split("/commons/")
        if len(parts) == 2:
            path = parts[1]
            filename = os.path.basename(path)
            return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{path}/200px-{filename}.png"
    return url

def load_image_from_url(url):
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        url = sanitize_url(url)
        filename = os.path.basename(url.split("?")[0])
        cache_path = os.path.join(CACHE_DIR, filename)
        
        if os.path.exists(cache_path):
            return Image.open(cache_path)

        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        img.save(cache_path)
        return img
    except Exception:
        return None

# ---------------------------------------------------------
# 3. ADVANCED NEON GRAPHICS ENGINE
# ---------------------------------------------------------
def draw_hud_box(draw, bbox, outline_color, fill_color=(10, 15, 26, 200), radius=15, width=2):
    x1, y1, x2, y2 = bbox
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill_color, outline=outline_color, width=width)
    
    corner_len = 18
    draw.line([(x1 - 4, y1 + corner_len), (x1 - 4, y1 - 4), (x1 + corner_len, y1 - 4)], fill=outline_color, width=3)
    draw.line([(x2 + 4 - corner_len, y1 - 4), (x2 + 4, y1 - 4), (x2 + 4, y1 + corner_len)], fill=outline_color, width=3)
    draw.line([(x1 - 4, y2 - corner_len), (x1 - 4, y2 + 4), (x1 + corner_len, y2 + 4)], fill=outline_color, width=3)
    draw.line([(x2 + 4 - corner_len, y2 + 4), (x2 + 4, y2 + 4), (x2 + 4, y2 - corner_len)], fill=outline_color, width=3)

def render_cyberpunk_frame(df_frame, year_label, frame_idx, style_key="cyber_pulse", width=1920, height=1080):
    img = Image.new("RGBA", (width, height), (10, 14, 23, 255))
    draw = ImageDraw.Draw(img)

    style_cfg = ANIMATION_STYLES.get(style_key, ANIMATION_STYLES['cyber_pulse'])

    if style_cfg['pulse_glow']:
        pulse = (math.sin(frame_idx * 0.15) + 1) / 2
    else:
        pulse = 0.5

    # Main Outer HUD Container
    hud_glow_alpha = int(120 + 60 * pulse)
    draw_hud_box(draw, (40, 40, width - 40, height - 40), outline_color=(0, 255, 128, hud_glow_alpha), fill_color=(12, 18, 30, 220), radius=20, width=2)
    
    # Header & Year Pods
    draw_hud_box(draw, (80, 70, 600, 200), outline_color=(0, 255, 128, 180), fill_color=(8, 12, 20, 240), radius=12, width=2)
    draw.text((120, 90), "NYC MUSLIM POPULATION", font=get_font(28), fill=(240, 245, 255))
    draw.text((120, 125), "• BAR CHART RACE •", font=get_font(20), fill=(0, 255, 128))
    draw.text((120, 155), f"STYLE: {style_cfg['label'].upper()}", font=get_font(18), fill=(130, 150, 180))

    draw_hud_box(draw, (width - 550, 70, width - 80, 200), outline_color=(0, 255, 128, 200), fill_color=(8, 12, 20, 240), radius=12, width=2)
    draw.text((width - 510, 105), "YEAR:", font=get_font(42), fill=(220, 235, 255))
    draw.text((width - 320, 95), str(year_label), font=get_font(60), fill=(0, 255, 128))

    df_sorted = df_frame.sort_values(by="Value", ascending=False).reset_index(drop=True)
    max_val = df_sorted['Value'].max() * 1.25 if not df_sorted.empty and df_sorted['Value'].max() > 0 else 100
    
    y_start, y_spacing = 280, 180
    bar_x_start, max_bar_width, bar_h = 480, 800, 75

    font_cat, font_val = get_font(38), get_font(44)

    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    for i, row in df_sorted.iterrows():
        y = y_start + (i * y_spacing)
        val = row['Value']
        cat_raw = str(row['Category']).upper()
        
        c_info = derive_color_profile(row.get('Color', '#00E5FF'))
        main_c = c_info['main']
        glow_c = c_info['glow']
        dark_c = c_info['dark']

        # Category Name (Left Aligned)
        draw.text((400, y + 15), cat_raw, font=font_cat, fill=(255, 255, 255), anchor="rm")

        # Indicator Dot
        dot_x, dot_y = 430, y + 38
        draw.ellipse([dot_x - 10, dot_y - 10, dot_x + 10, dot_y + 10], fill=main_c)
        glow_draw.ellipse([dot_x - 18, dot_y - 18, dot_x + 18, dot_y + 18], fill=glow_c + (int(150 + 80 * pulse),))

        # Dynamic Bar Calculations
        calc_len = (val / max_val) * max_bar_width if max_val > 0 else 20
        fill_bar_x2 = bar_x_start + calc_len
        
        # Capsule outline tracks the growing bar fill edge
        capsule_x2 = fill_bar_x2 + 10

        # --- DYNAMIC NEON CONTAINER OUTLINE ---
        draw.rounded_rectangle(
            [bar_x_start - 10, y - 5, capsule_x2, y + bar_h + 5],
            radius=20,
            fill=(dark_c[0], dark_c[1], dark_c[2], 180),
            outline=main_c + (160,),
            width=2
        )

        # --- INNER ACTIVE FILLED BAR ---
        draw.rounded_rectangle(
            [bar_x_start, y, fill_bar_x2, y + bar_h],
            radius=15,
            fill=main_c + (230,),
            outline=glow_c + (255,),
            width=2
        )

        # Specular Highlight Line
        if calc_len > 30:
            draw.line([(bar_x_start + 15, y + 6), (fill_bar_x2 - 15, y + 6)], fill=(255, 255, 255, 200), width=3)

        # Pulsing Glow Pass
        glow_w = int(4 + 4 * pulse) if style_cfg['pulse_glow'] else 6
        glow_draw.rounded_rectangle(
            [bar_x_start - glow_w, y - glow_w, fill_bar_x2 + glow_w, y + bar_h + glow_w],
            radius=18,
            outline=glow_c + (int(180 + 75 * pulse),),
            width=glow_w
        )

        # --- NUMERICAL LABEL (Positioned Outside the Dynamic Outline Capsule) ---
        val_str = f"{int(val):,}"
        draw.text((capsule_x2 + 20, y + 12), val_str, font=font_val, fill=main_c)

    # OpenCV Gaussian Bloom
    glow_np = np.array(glow_layer)
    blurred_glow = cv2.GaussianBlur(glow_np, (35, 35), 0)
    glow_pil = Image.fromarray(blurred_glow)

    final_img = Image.alpha_composite(img, glow_pil)
    return np.array(final_img.convert("RGB"))

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
            linear_alpha = f / frames_per_year
            
            style_key = default_style
            if 'AnimationStyle' in df.columns and not df['AnimationStyle'].dropna().empty:
                style_key = str(df['AnimationStyle'].iloc[0]).lower()
            
            easing_func = ANIMATION_STYLES.get(style_key, ANIMATION_STYLES['cyber_pulse'])['easing']
            eased_alpha = easing_func(linear_alpha)
            
            current_year_val = int(y0 + linear_alpha * (y1 - y0))
            
            for cat in categories:
                v0 = df0.loc[cat, 'Value'] if cat in df0.index else 0
                v1 = df1.loc[cat, 'Value'] if cat in df1.index else 0
                
                v_interp = v0 + eased_alpha * (v1 - v0)
                
                logo = df0.loc[cat, 'LogoUrl'] if cat in df0.index else ""
                color_val = df0.loc[cat, 'Color'] if ('Color' in df0.columns and cat in df0.index) else "#00E5FF"
                
                interp_records.append({
                    'Frame': len(interp_records) // len(categories),
                    'YearLabel': current_year_val,
                    'Category': cat,
                    'Value': v_interp,
                    'LogoUrl': logo,
                    'Color': color_val,
                    'Style': style_key
                })

    df_interp = pd.DataFrame(interp_records)
    max_frame = df_interp['Frame'].max()

    def make_frame(t):
        frame_idx = int(t * fps)
        frame_idx = min(frame_idx, max_frame)
        
        sub_df = df_interp[df_interp['Frame'] == frame_idx]
        year_lbl = sub_df['YearLabel'].iloc[0] if not sub_df.empty else ""
        style_used = sub_df['Style'].iloc[0] if not sub_df.empty else default_style
        return render_cyberpunk_frame(sub_df, year_label=year_lbl, frame_idx=frame_idx, style_key=style_used)

    duration = total_frames / fps
    clip = VideoClip(make_frame, duration=duration)
    clip.write_videofile(output_path, fps=fps, codec='libx264', audio=False)
    print(f"\nHD Video successfully saved to {output_path}!")

if __name__ == "__main__":
    df = pd.read_csv(CSV_PATH)
    generate_race_video(df, output_path="bar_chart_race.mp4", default_style="cyber_pulse")