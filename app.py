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
                "protein_cost_per_g": {"type": "STRING"},
                "pfc_balance_eval": {"type": "STRING"},
                "detected_traps": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                }
            },
            "required": ["protein_cost_per_g", "pfc_balance_eval", "detected_traps"]
        },
        "toxic_review": {"type": "STRING"}
    },
    "required": ["product_name", "pricing", "slot_judgment", "koyaku_and_traps", "toxic_review"]
}

SYSTEM_INSTRUCTION = (
    "あなたは冷徹なコスパ分析力と毒舌なパチスロ知識を併せ持つ「惣菜設定判別エージェント」です。\n"
    "ユーザーから提供された弁当・惣菜の画像を精査し、見かけの定価や割引率のアンカリングを粉砕して「実質的な価格の妥当性」を設定（1〜6）および機械割として判定してください。\n\n"
    "【設定判別ロジック・小役確率テーブル】\n"
    "1. タンパク質単価（強チェリー/ベル確率に相当）: 実支払額÷タンパク質推定重量(g)を算出。\n"
    "   20円以下/g: 設定6（神コスパ）、20〜28円/g: 設定4〜5、28〜38円/g: 設定2〜3、40円以上/gまたはタンパク質10g未満: 設定1（即ヤメ）。\n"
    "2. 原材料・おかず構成（朝イチリセット判定）: 原材料表示の先頭が肉魚なら高設定示唆。米やパン粉が先頭なら低設定据え置き。ご飯が全体の60%超なら炭水化物ビッグボーナス（減点）。\n"
    "3. フェイク前兆看破: 衣50%超は衣詐欺（ガセ前兆）。容器中央の隆起は上げ底リブ（CZスルー天井）。主菜下の無味パスタは絨毯パスタ（高確詐欺）。\n"
    "4. 設定示唆トロフィー: 設定1=示唆なし（通常終了画面）、設定2=銅、設定3=銀、設定4=金、設定5=キリン柄、設定6=虹。\n"
    "5. トーン＆マナー: パチスロ用語（子役、天井、朝イチ、ツモ、据え置き、ベタピン、ガセ前兆、直撃）を散りばめた毒舌立ち回りレビューを出力してください。"
)

uploaded_file = st.file_uploader("惣菜・弁当・シールの写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="判別対象の台", use_container_width=True)
    
    if st.button("設定推測レバーを叩く！ 🎰", type="primary"):
        with st.spinner("出目とリール（衣率・上げ底・タンパク質）を解析中..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
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
                
                j = result["slot_judgment"]
                col1, col2, col3 = st.columns(3)
                col1.metric("推定設定", f"設定 {j['setting']}")
                col2.metric("機械割", f"{j['payout_rate']}%")
                col3.metric("立ち回り", j['action'])
                
                trophy = j["trophy"]
                trophy_badge = {
                    "虹": "<span class='badge-rainbow'>🌈 虹トロフィー（設定6濃厚）</span>",
                    "キリン柄": "<span class='badge-kirin'>🦒 キリン柄トロフィー（設定5以上）</span>",
                    "金": "<span class='badge-gold'>🥇 金トロフィー（設定4以上）</span>",
                    "銀": "<span class='badge-silver'>🥈 銀トロフィー（設定3以上）</span>",
                    "銅": "<span class='badge-bronze'>🥉 銅トロフィー（設定2以上）</span>",
                    "示唆なし": "<span class='badge-none'>通常終了画面（示唆なし・ベタピン濃厚）</span>"
                }.get(trophy, "<span class='badge-none'>示唆なし</span>")
                
                st.markdown(f"**確定演出・示唆**: {trophy_badge}", unsafe_allow_html=True)
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
                
                st.markdown("---")
                
                st.markdown("#### 🍒 小役確率 & フェイク前兆検知")
                k = result["koyaku_and_traps"]
                st.write(f"- **タンパク質単価（強小役）**: `{k['protein_cost_per_g']}`")
                st.write(f"- **PFC構成（炭水化物比率）**: {k['pfc_balance_eval']}")
                
                traps = k.get("detected_traps", [])
                if traps:
                    trap_html = " ".join([f"<span class='trap-chip'>⚠️ {t}</span>" for t in traps])
                    st.markdown(f"**検知されたトラップ**: {trap_html}", unsafe_allow_html=True)
                else:
                    st.write("**検知されたトラップ**: なし（クリーンな優良仕様）")
                
                st.markdown("---")
                
                st.markdown("#### 🗣️ ホール講評（毒舌アドバイス）")
                st.info(result["toxic_review"])
                
            except Exception as e:
                st.error(f"判別中にエラーが発生しました: {str(e)}")
