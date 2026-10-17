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
                "trophy": {"type": "STRING", "enum": ["示唆なし", "銅", "銀", "金", "キリン柄", "虹"]},
                "action": {"type": "STRING"}
            },
            "required": ["setting", "payout_rate", "trophy", "action"]
        },
        "koyaku_and_traps": {
            "type": "OBJECT",
            "properties": {
                "core_metric_eval": {"type": "STRING"},
                "balance_eval": {"type": "STRING"},
                "detected_traps": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                }
            },
            "required": ["core_metric_eval", "balance_eval", "detected_traps"]
        },
        "toxic_review": {"type": "STRING"}
    },
    "required": ["product_name", "genre", "pricing", "slot_judgment", "koyaku_and_traps", "toxic_review"]
}

SYSTEM_INSTRUCTION = (
    "あなたは冷徹なコスパ分析力と毒舌なパチスロ知識を併せ持つ「惣菜設定判別エージェント」です。\n"
    "料理の性質を無視して一律にタンパク質至上主義で判定することは厳禁です。\n"
    "1. 【肉・揚げ物・がっつり弁当系】（AT機スペック）: 実支払額÷タンパク質推定重量(g)を重視。20円以下/gは設定6、40円以上/gまたは10g未満は設定1。衣詐欺や上げ底は減点。\n"
    "2. 【おこわ・炊き込みご飯・助六・和食系】（Aタイプスペック）: タンパク質単価の減点を解除。もち米の質、出汁の染み込み、季節具材（栗・茸・山菜等）の充実度と職人仕込み感を評価。400円台で丁寧なおこわは設定4〜5が適正。\n"
    "3. 設定示唆トロフィー: 1=示唆なし、2=銅、3=銀、4=金、5=キリン柄、6=虹。\n"
    "4. パチスロ用語（子役、天井、朝イチ、据え置き、ベタピン、ガセ前兆、直撃、Aタイプ、純増）を交えて毒舌かつ的確な立ち回りレビューを出力してください。"
)

uploaded_file = st.file_uploader("惣菜・弁当・シールの写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="判別対象の台", use_container_width=True)
    
    if st.button("設定推測レバーを叩く！ 🎰", type="primary"):
        with st.spinner("出目とリール（ジャンル判別・素材・価格）を解析中..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[image, "この商品のジャンル特性を考慮して設定と価格妥当性を判別してください。"],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                        temperature=0.3
                    )
                )
                
                result = json.loads(response.text)
                
                st.subheader(f"🔍 判定台: {result['product_name']}")
                st.caption(f"スペック分類: {result.get('genre', '一般惣菜')}")
                
                j = result["slot_judgment"]
                col1, col2, col3 = st.columns(3)
                col1.metric("推定設定", f"設定 {j['setting']}")
                col2.metric("機械割", f"{j['payout_rate']}%")
                col3.metric("立ち回り", j['action'])
                
                trophy = j
