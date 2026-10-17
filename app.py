SyntaxError: expected 'except' or 'finally' block は、GitHub上でコードを貼り付けた際に、117行目の trophy = j["trophy"] の途中で切れてしまい、それ以降のコード（except や画面描画処理）が丸ごと欠落してしまったことが原因です。   GitHubのWebエディタで貼り付ける際、長いコードだと末尾が欠けるトラブルを防ぐため、無駄な装飾や長いプロンプトを徹底的にスリム化し、行数を半分近くまで圧縮した軽量・安全版コードを用意しました。以下のコードをコピーし、GitHubの app.py の中身を全選択して消去した上で、そのまま貼り付けて保存（Commit changes）してください。軽量・安定版 app.py（全115行）Pythonimport os
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
                "traps": {"type": "ARRAY", "items": {"type": "STRING"}}
            },
            "required": ["core_eval", "traps"]
        },
        "toxic_review": {"type": "STRING"}
    },
    "required": ["product_name", "genre", "pricing", "slot_judgment", "features", "toxic_review"]
}

SYSTEM_INSTRUCTION = (
    "惣菜・弁当の画像から実質コスパを設定（1〜6）および機械割で判定するパチスロ風エージェントです。\n"
    "【重要ルール】料理ジャンルに合わせて判別基準を切り替えてください。\n"
    "1. 肉・揚げ物・がっつり弁当系（AT機）: タンパク質単価を重視。20円以下/gは設定6、40円以上/gや極端な上げ底・衣過多は設定1。\n"
    "2. おこわ・炊き込みご飯・助六寿司・和食系（Aタイプ）: タンパク質至上主義を解除。米・もち米の質、出汁、栗や茸などの季節具材の充実度を評価。400円前後で丁寧なおこわは設定4〜5が適正。\n"
    "トロフィーは 虹(6), キリン柄(5), 金(4), 銀(3), 銅(2), 示唆なし(1) から選定し、スロット用語混じりの毒舌講評を出力してください。"
)

uploaded_file = st.file_uploader("惣菜・弁当・シールの写真をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="判別対象の台", use_container_width=True)
    
    if st.button("設定推測レバーを叩く！ 🎰", type="primary"):
        with st.spinner("出目・リール・ジャンル特性を解析中..."):
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
                res = json.loads(response.text)
                
                st.subheader(f"🔍 判定台: {res['product_name']}")
                st.caption(f"スペック分類: {res.get('genre', '一般惣菜')}")
                
                j = res["slot_judgment"]
                col1, col2, col3 = st.columns(3)
                col1.metric("推定設定", f"設定 {j['setting']}")
                col2.metric("機械割", f"{j['payout_rate']}%")
                col3.metric("立ち回り", j['action'])
                
                t_cls = {"虹": "badge-rainbow", "キリン柄": "badge-kirin", "金": "badge-gold", "銀": "badge-silver", "銅": "badge-bronze"}.get(j["trophy"], "badge-none")
                st.markdown(f"**確定演出・示唆**: <span class='{t_cls}'>{j['trophy']}示唆</span>", unsafe_allow_html=True)
                st.markdown("---")
                
                p = res["pricing"]
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**定価**: ¥{p['list_price']:,}" if p['list_price'] else "**定価**: 不明")
                c2.write(f"**値引き**: {p['discount_type']}")
                c3.write(f"**実支払額**: ¥{p['pay_price']:,}" if p['pay_price'] else "**実支払額**: 不明")
                c4.write(f"**適正価格**: ¥{p['fair_price']:,}")
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
                
            except Exception as e:
                st.error(f"判別中にエラーが発生しました: {str(e)}")
