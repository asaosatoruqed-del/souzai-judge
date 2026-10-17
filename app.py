import os
import json
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="惣菜設定判別機", page_icon="🎰", layout="centered")

st.markdown("""
<style>
    .badge-rainbow { background: linear-gradient(45deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #8b00ff); color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; display: inline-block; }
    .badge-kirin { background: repeating-linear-gradient(45deg, #e6b422, #e6b422 10px, #331100 10px, #331100 20px); color: #fff; text-shadow: 1px 1px 2px #000; padding: 6px 12px; border-radius: 6px; font-weight: bold; display: inline-block; }
    .badge-gold { background-color: #ffd700; color: #000; padding: 6px 12px; border-radius: 6px; font-weight: bold; display: inline-block; }
    .badge-silver { background-color: #c0c0c0; color: #000; padding: 6px 12px; border-radius: 6px; font-weight: bold; display: inline-block; }
    .badge-bronze { background-color: #cd7f32; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; display: inline-block; }
    .badge-none { background-color: #33333e; color: #aaa; padding: 6px 12px; border-radius: 6px; display: inline-block; }
    .trap-chip { background-color: #4a1515; color: #ff8888; border: 1px solid #aa3333; padding: 3px 8px; border-radius: 4px; margin-right: 5px; font-size: 0.85em; display: inline-block; }
    .good-chip { background-color: #153e20; color: #88ffaa; border: 1px solid #2e7d32; padding: 3px 8px; border-radius: 4px; margin-right: 5px; font-size: 0.85em; display: inline-block; }
</style>
""", unsafe_allow_html=True)

st.title("🎰 惣菜・弁当 設定判別機")
st.caption("値引きシールの魔力に騙されるな。真の機械割と実力価格を暴くエージェント。")

api_key = st.secrets.get("GEMINI_API_KEY") if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets else os.environ.get("GEMINI_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Gemini API Key を入力", type="password")
    if not api_key:
        st.info("サイドバーにGemini API Keyを入力するか、StreamlitのSecretsに設定してください。")
        st.stop()

client = genai.Client(api_key=api_key)

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "product_name": {"type": "STRING"},
        "genre": {"type": "STRING", "description": "弁当・肉惣菜 / 伝統和食・飯もの・寿司 / 揚げ物・一品 など"},
        "pricing": {
            "type": "OBJECT",
            "properties": {
                "list_price": {"type": "INTEGER", "nullable": True},
                "discount_type": {"type": "STRING"},
                "pay_price": {"type": "INTEGER", "nullable": True},
                "fair_price": {"type": "INTEGER"}
            },
            "required": ["list_price", "discount_type", "pay_price", "fair_price"]
        },
        "slot_judgment": {
            "type": "OBJECT",
            "properties": {
                "setting": {"type": "INTEGER"},
                "payout_rate": {"type": "NUMBER"},
                "trophy": {"type": "STRING", "enum": ["示唆なし", "銅", "銀", "金", "キリン柄", "虹"]},
                "action": {"type": "STRING"}
            },
            "required": ["setting", "payout_rate", "trophy", "action"]
        },
        "koyaku_and_traps": {
            "type": "OBJECT",
            "properties": {
