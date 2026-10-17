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
    .badge-gold { background-color: #ffd700; color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-silver { background-color: #c0c0c0; color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-bronze { background-color: #cd7f32; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-none { background-color: #444; color: white; padding: 4px 8px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

st.title("🎰 惣菜・弁当 設定判別機")
st.caption("値引きシールの魔力に騙されるな。真の機械割と実力価格を暴くエージェント。")

# Streamlit Secrets または 環境変数 または 手動入力 からキーを取得
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
        "traps_and_features": {
            "type": "OBJECT",
            "properties": {
                "batter_ratio": {"type": "STRING"},
                "raised_bottom": {"type": "STRING"},
                "protein_yield": {"type": "STRING"}
            },
            "required": ["batter_ratio", "raised_bottom", "protein_yield"]
        },
        "toxic_review": {"type": "STRING"}
    },
    "required": ["product_name", "pricing", "slot_judgment", "traps_and_features", "toxic_review"]
}

SYSTEM_INSTRUCTION = """
あなたは冷徹なコスパ分析力と毒舌なパチスロ知識を併せ持つ「惣菜設定判別エージェント」です。
ユーザーから提供された弁当・惣菜の画像を分析し、見かけの定価や割引率のアンカリングを粉砕して「実質的な価格の妥当性」を設定（1〜6）および機械割として判定してください。

【分析ルール】
1. 価格・割引の解析: 定価、割引シール、実支払額を抽出。
2. 罠（フェイク要素）の検出: 衣詐欺、底上げ容器の隆起、不自然に敷かれたスパゲティ、タンパク質の少なさ。
3. 設定定義:
   - 設定1: 上げ底・衣率50%超・定価吊り上げ後のフェイク半額。機械割97%未満。
   - 設定2: 炭水化物爆弾。安かろう悪かろう。機械割98.5%前後。
   - 設定3: 割引シールでようやく等価交換。機械割101.0%前後。
   - 設定4: 堅実台。肉質十分、かさ増し控えめ。機械割104.5%前後。
   - 設定5: 元値の高い良質惣菜の割引。素材勝ち。機械割108.5%前後。
   - 設定6: 原価率破壊、容器のフタが浮く肉量、神コスパ。機械割114.9%前後。
4. トーン＆マナー:
   - パチスロ用語（子役、天井、朝イチ、ツモ、ベタピン、トロフィー、示唆、目押し）を交えた毒舌な立ち回りアドバイス。
"""

uploaded_file = st.file_uploader("惣菜・弁当・シールの写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="判別対象の台", use_container_width=True)
    
    if st.button("設定推測レバーを叩く！ 🎰", type="primary"):
        with st.spinner("出目とリール（衣率・上げ底）を解析中..."):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[image, "この惣菜・弁当の設定と価格妥当性を判別してください。"],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                        temperature=0.3
                    )
                )
                
                result = json.loads(response.text)
                
                st.subheader(f"🔍 判定台: {result['product_name']}")
                
                setting = result["slot_judgment"]["setting"]
                payout = result["slot_judgment"]["payout_rate"]
                action = result["slot_judgment"]["action"]
                trophy = result["slot_judgment"]["trophy"]
                
                col1, col2, col3 = st.columns(3)
                col1.metric("推定設定", f"設定 {setting}")
                col2.metric("推定機械割", f"{payout}%")
                col3.metric("立ち回り", action)
                
                trophy_class = {
                    "虹": "badge-rainbow",
                    "キリン柄": "badge-gold",
                    "金": "badge-gold",
                    "銀": "badge-silver",
                    "銅": "badge-bronze"
                }.get(trophy, "badge-none")
                
                st.markdown(f"**確定演出・示唆**: <span class='{trophy_class}'>{trophy}トロフィー</span>", unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("#### 💰 価格・収支バランス")
                p = result["pricing"]
                list_p = f"¥{p['list_price']:,}" if p['list_price'] else "不明"
                pay_p = f"¥{p['pay_price']:,}" if p['pay_price'] else "不明"
                fair_p = f"¥{p['fair_price']:,}"
                
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**定価**: {list_p}")
                c2.write(f"**値引き**: {p['discount_type']}")
                c3.write(f"**実支払額**: {pay_p}")
                c4.write(f"**適正価格**: {fair_p}")
                
                st.markdown("#### ⚠️ フェイク・トラップ検知")
                t = result["traps_and_features"]
                st.write(f"- **衣比率**: {t['batter_ratio']}")
                st.write(f"- **底上げ（上げ底）**: {t['raised_bottom']}")
                st.write(f"- **タンパク質コスパ**: {t['protein_yield']}")
                
                st.markdown("---")
                st.markdown("#### 🗣️ ホール講評（毒舌アドバイス）")
                st.info(result["toxic_review"])
                
            except Exception as e:
                st.error(f"判別中にエラーが発生しました: {str(e)}")
