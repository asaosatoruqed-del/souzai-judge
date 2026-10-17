import os
import json
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="惣菜設定判別機", page_icon="🎰", layout="centered")

st.markdown("""
<style>
    .badge-rainbow { background: linear-gradient(45deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #8b00ff); color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-kirin { background: #e6b422; color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-gold { background-color: #ffd700; color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-silver { background-color: #c0c0c0; color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-bronze { background-color: #cd7f32; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-none { background: #444; color: #aaa; padding: 4px 8px; border-radius: 4px; }
    .trap-chip { background: #4a1515; color: #ff8888; border: 1px solid #aa3333; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; margin-right: 4px; }
</style>
""", unsafe_allow_html=True)

# 入口は極めてシンプルに
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
        "genre": {"type": "STRING"},
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
                "trophy": {"type": "STRING"},
                "action": {"type": "STRING"}
            },
            "required": ["setting", "payout_rate", "trophy", "action"]
        },
        "features": {
            "type": "OBJECT",
            "properties": {
                "core_eval": {"type": "STRING"},
                "traps": {"type": "ARRAY", "items": {"type": "STRING"}},
                "road_to_setting6": {
                    "type": "OBJECT",
                    "properties": {
                        "price_condition": {"type": "STRING", "description": "価格変動（いくらの割引や半額シールが付けば設定6に化けるか）"},
                        "content_condition": {"type": "STRING", "description": "内容変更（どんな具材や肉厚・仕込みがあれば定価でも設定6だったか）"}
                    },
                    "required": ["price_condition", "content_condition"]
                }
            },
            "required": ["core_eval", "traps", "road_to_setting6"]
        },
        "toxic_review": {"type": "STRING"}
    },
    "required": ["product_name", "genre", "pricing", "slot_judgment", "features", "toxic_review"]
}

SYSTEM_INSTRUCTION = (
    "惣菜・弁当の画像から実質コスパを設定（1〜6）および機械割で判定するパチスロ風エージェントです。\n"
    "【料理ジャンル別スペック】\n"
    "1. 肉・揚げ物・弁当（AT機）: タンパク質単価を重視。20円以下/gは設定6、40円以上/gや過剰な衣・上げ底は設定1。\n"
    "2. おこわ・炊き込みご飯・助六・和食（Aタイプ）: タンパク質単価減点を解除。米質、出汁、栗や茸などの季節具材を評価。400円台で丁寧なおこわは設定4〜5が適正。\n"
    "【設定6（虹トロフィー・機械割114.9%以上）への2大昇格ルートの提示】\n"
    "判定の最後に、この台が設定6になるための条件を具体的に出力すること。\n"
    "- price_condition: 価格変動（例: 半額シール直撃で○○円以下になれば機械割115%超のバグ台へ昇格）\n"
    "- content_condition: 内容変更（例: 栗が丸ごと大粒で入っている、または肉厚が倍あれば定価でも設定6）\n"
    "トロフィーは 虹(6), キリン柄(5), 金(4), 銀(3), 銅(2), 示唆なし(1) から選定し、毒舌かつ的確な立ち回りレビューを出力してください。"
)

uploaded_file = st.file_uploader("惣菜・弁当・シールの写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="判別対象の台", use_container_width=True)
    
    if st.button("設定推測レバーを叩く！ 🎰", type="primary"):
        with st.spinner("出目・リール・設定6昇格条件を解析中..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[image, "この商品のジャンル特性を考慮して設定と価格妥当性を判別し、設定6への昇格条件も教えてください。"],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                        temperature
