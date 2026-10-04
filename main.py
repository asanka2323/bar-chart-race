import streamlit as st
import pandas as pd
from app import generate_race_video

st.title("Cyberpunk Bar Chart Race Generator")

uploaded_file = st.file_uploader("Upload CSV Data", type=["csv"])
style = st.selectbox("Animation Style", ["cyber_pulse", "smooth", "elastic_pop", "bounce", "linear"])

if uploaded_file and st.button("Generate Video"):
    df = pd.read_csv(uploaded_file)
    with st.spinner("Rendering HD Video..."):
        generate_race_video(df, output_path="output.mp4", default_style=style)
    st.video("output.mp4")
    with open("output.mp4", "rb") as file:
        st.download_button("Download Video", file, file_name="bar_chart_race.mp4")