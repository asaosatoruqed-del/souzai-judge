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
    .badge-gold { background: #ffd700; color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-silver { background: #c0c0c0; color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-bronze { background: #cd7f32; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-none { background: #444; color: #aaa; padding: 4px 8px; border-radius: 4px; }
    .trap-chip { background: #4a1515; color: #ff8888; border: 1px solid #aa3333; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; margin-right: 4px; }
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
                "price_to_6": {"type": "STRING"},
                "content_to_6": {"type": "STRING"}
            },
            "required": ["core_eval", "traps", "price_to_6", "content_to_6"]
        },
        "toxic_review": {"type": "STRING"}
    },
    "required": ["product_name", "genre", "pricing", "slot_judgment", "features", "toxic_review"]
}

SYSTEM_INSTRUCTION = (
    "惣菜・弁当の画像から実質コスパを設定（1〜6）および機械割で判定するパチスロ風エージェントです。\n"
    "【ジャンル別】\n"
    "1. 肉・揚げ物・弁当（AT機）: タンパク質単価を重視。20円以下/gは設定6、40円以上/gや過剰な衣・上げ底は設定1。\n"
    "2. おこわ・和食（Aタイプ）: タンパク質単価減点を解除。米質、出汁、季節具材を評価。400円台の丁寧なおこわは設定4〜5が適正。\n"
    "【設定6（虹・機械割115%超）への2大昇格ルート】\n"
    "- price_to_6: 価格変動（例: 半額シール直撃で○○円以下なら設定6昇格）\n"
    "- content_to_6: 内容変更（例: 栗が丸ごと大粒で入っている、または肉厚が倍あれば定価でも設定6）\n"
    "トロフィーは 虹(6), キリン柄(5), 金(4), 銀(3), 銅(2), 示唆なし(1) から選定し、毒舌立ち回りレビューを出力してください。"
)

uploaded_file = st.file_uploader("惣菜・弁当・シールの写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="判別対象の台", use_container_width=True)
    
    if st.button("設定推測レバーを叩く！ 🎰", type="primary"):
        with st.spinner("出目・リール・設定6昇格条件を解析中..."):
            try:
                cfg = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    temperature=0.3
                )
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[image, "この商品の設定判別と設定6への昇格条件を出力してください。"],
                    config=cfg
                )
                res = json.loads(response.text)
                
                st.subheader(f"🔍 判定台: {res['product_name']}")
                st.caption(f"スペック分類: {res.get('genre', '一般惣菜')}")
                
                j = res["slot_judgment"]
                c1, c2, c3 = st.columns(3)
                c1.metric("推定設定", f"設定 {j['setting']}")
                c2.metric("機械割", f"{j['payout_rate']}%")
                c3.metric("立ち回り", j['action'])
                
                t_cls = {"虹": "badge-rainbow", "キリン柄": "badge-kirin", "金": "badge-gold", "銀": "badge-silver", "銅": "badge-bronze"}.get(j["trophy"], "badge-none")
                st.markdown(f"**確定演出・示唆**: <span class='{t_cls}'>{j['trophy']}示唆</span>", unsafe_allow_html=True)
                st.markdown("---")
                
                p = res["pricing"]
                p1, p2, p3, p4 = st.columns(4)
                p1.write(f"**定価**: ¥{p['list_price']:,}" if p['list_price'] else "**定価**: 不明")
                p2.write(f"**値引き**: {p['discount_type']}")
                p3.write(f"**実支払額**: ¥{p['pay_price']:,}" if p['pay_price'] else "**実支払額**: 不明")
                p4.write(f"**適正価格**: ¥{p['fair_price']:,}")
                st.markdown("---")
                
                f = res["features"]
                st.markdown("#### 🍒 特性 & トラップ検知")
                st.write(f"- **メイン評価**: {f['core_eval']}")
                traps = f.get("traps", [])
                if traps:
                    st.markdown("**検知されたトラップ**: " + " ".join([f"<span class='trap-chip'>⚠️ {t}</span>" for t in traps]), unsafe_allow_html=True)
                else:
                    st.write("**検知されたトラップ**: なし（優良仕様）")
                st.markdown("---")
                
                st.markdown("#### 🗣️ ホール講評（立ち回りアドバイス）")
                st.info(res["toxic_review"])
                st.markdown("---")
                
                st.warning(
                    f"**🔥 さらに上（設定6）を目指すには！？【立ち回り指南】**\n\n"
                    f"- 📉 **価格変動ルート**: {f.get('price_to_6', '半額シール直撃を待て')}\n\n"
                    f"- 🥩 **内容変更ルート**: {f.get('content_to_6', '素材の原価破壊仕様を探せ')}"
                )
            except Exception as e:
                st.error(f"判別中にエラーが発生しました: {str(e)}")
