import os
import json
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="惣菜設定判別機", page_icon="🎰", layout="centered")

st.markdown("""
<style>
    .badge-rainbow { background: linear-gradient(45deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #8b00ff); color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .badge-kirin { background: #e6b422; color: #000; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .badge-gold { background-color: #ffd700; color: #000; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .badge-silver { background-color: #c0c0c0; color: #000; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .badge-bronze { background-color: #cd7f32; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .badge-none { background-color: #33333e; color: #888; padding: 4px 10px; border-radius: 4px; }
    
    .point-chip {
        background-color: #262730;
        color: #cfd2dc;
        border: 1px solid #3d4051;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 0.88em;
        margin-right: 6px;
        margin-bottom: 6px;
        display: inline-block;
    }
    
    .action-box {
        background-color: #1e1e2d;
        border-left: 4px solid #4ade80;
        padding: 10px 14px;
        border-radius: 4px;
        margin-top: 8px;
        margin-bottom: 12px;
        font-size: 0.95em;
        line-height: 1.5;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎰 惣菜・弁当 設定判別機")
st.caption("値引きシールの魔力に騙されるな。真の機械割と実力価格を暴くエージェント。")

st.sidebar.header("⚙️ 実戦ホール設定")
region = st.sidebar.selectbox(
    "実戦エリア",
    ["東海・沖縄エリア（ハナハナ王国）", "関東・その他全国（ジャグラー王国）"],
    index=0
)

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
                "trophy": {"type": "STRING", "enum": ["なし", "ブロンズ", "シルバー", "ゴールド", "キリン柄", "レインボー"]},
                "action": {"type": "STRING"}
            },
            "required": ["setting", "payout_rate", "trophy", "action"]
        },
        "features": {
            "type": "OBJECT",
            "properties": {
                "core_eval": {"type": "STRING"},
                "checkpoints": {"type": "ARRAY", "items": {"type": "STRING"}},
                "price_to_6": {"type": "STRING"},
                "content_to_6": {"type": "STRING"}
            },
            "required": ["core_eval", "checkpoints", "price_to_6", "content_to_6"]
        },
        "toxic_review": {"type": "STRING"}
    },
    "required": ["product_name", "genre", "pricing", "slot_judgment", "features", "toxic_review"]
}

if "東海" in region:
    a_type_rule = (
        "2. おこわ・和食・米主役（完全告知Aタイプ・ハナハナ仕様）: タンパク質単価の減点は解除。"
        "米質、出汁、季節具材の充実度を評価。丁寧に炊かれた400円台のおこわは設定4（ゴールド）以上で安定。"
        "ノーマルAタイプの比喩は徹底して「ハナハナ（華・ハイビスカス・チカり・先告知・プレミアム点滅）」を用いて講評してください。"
    )
    a_type_icon = "🌺"
else:
    a_type_rule = (
        "2. おこわ・和食・米主役（完全告知Aタイプ・ジャグラー仕様）: タンパク質単価の減点は解除。"
        "米質、出汁、季節具材の充実度を評価。丁寧に炊かれた400円台のおこわは設定4（ゴールド）以上で安定。"
        "ノーマルAタイプの比喩は徹底して「ジャグラー（GOGOランプ・ペカり・ガコッ・後告知・ぶどう逆算）」を用いて講評してください。"
    )
    a_type_icon = "🤡"

SYSTEM_INSTRUCTION = (
    "惣菜・弁当の画像およびユーザーの実戦メモから、実質コスパを設定（1〜6）および機械割で判定するパチスロ風エージェントです。\n\n"
    "【ユーザー補足情報（実戦メモ）の厳格な仕分け・超重要ルール】\n"
    "ユーザーのメモを『物理ファクト』と『主観オカルト』に冷徹に峻別すること。\n"
    "1. 物理ファクト（判定に反映OK）: 「持ったらズッシリ重い」「底上げが3cmある」「肉が極薄」「二重シールで下が40%引」等の客観的物理データのみを設定・機械割の計算に反映する。\n"
    "2. 主観オカルト・伝聞（判定への加点・減点は絶対厳禁）: 「友人が美味いと言っていた」「評判が良い」「店員が美人」「なんとなく出そう」「テレビで見た」等は、設定や機械割の数値に1ミリも加点してはならない！\n"
    "   もしそのようなオカルトが書かれていた場合、講評で『連れのオススメという名のガセナビに惑わされるな』『味の感想というオカルトで設定を盛るな、見るべきは肉量と価格の数字だ』とビシッと冷徹に釘を刺すこと。\n\n"
    "【立ち回り鉄則】\n"
    "・設定4以上（機械割104%超）: 定価でも迷わず即買い・キープ推奨！設定4確定なら腰を据えてツモるのがプロの鉄則。値引きを待つ必要は一切ない。\n"
    "・設定3以下（機械割101%未満）: 定価ではスルー・即ヤメ推奨。夕方以降の値引きシール（CZ）が付くまで見送り。\n\n"
    "【料理ジャンル別スペック】\n"
    "1. 肉・揚げ物・がっつり弁当（AT機）: タンパク質単価を重視。20円以下/gは設定6、40円以上/gや過剰な衣・上げ底は設定1。\n"
    f"{a_type_rule}\n\n"
    "【トロフィー命名規則（厳守）】\n"
    "設定1: なし、設定2: ブロンズ、設定3: シルバー、設定4: ゴールド、設定5: キリン柄、設定6: レインボー\n\n"
    "【講評の注意点】\n"
    "実戦エリアは前提なので、講評冒頭で『○○エリアにおいて〜』等の前フリは一切禁止です。最初から本題の演出・アドバイスから述べてください。\n\n"
    "【設定6（レインボー・機械割115%超）への2大昇格ルート】\n"
    "- price_to_6: 価格変動（例: 半額シール直撃で○○円以下なら設定6昇格）\n"
    "- content_to_6: 内容変更（例: 大粒栗の丸ごと投入、松茸スライス等で定価でも設定6）"
)

if "user_memo_val" not in st.session_state:
    st.session_state["user_memo_val"] = ""
if "last_uploaded_names" not in st.session_state:
    st.session_state["last_uploaded_names"] = []

uploaded_files = st.file_uploader(
    "惣菜・弁当・シールの写真をアップロード（複数枚OK）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

current_names = [f.name for f in uploaded_files] if uploaded_files else []
if current_names != st.session_state["last_uploaded_names"]:
    st.session_state["user_memo_val"] = ""
    st.session_state["last_uploaded_names"] = current_names

col_memo, col_clear = st.columns([5, 1])
with col_memo:
    user_memo = st.text_input(
        "打手の実戦メモ（任意）",
        value=st.session_state["user_memo_val"],
        key="memo_input",
        placeholder="例: 底が3cmくらい隆起してる、持ったら異常にズッシリ重い、シールの下にもう1枚シールがある、等"
    )
    st.session_state["user_memo_val"] = user_memo

with col_clear:
    st.write("")
    st.write("")
    if st.button("メモ消去"):
        st.session_state["user_memo_val"] = ""
        st.rerun()

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    cols = st.columns(min(len(images), 3))
    for idx, img in enumerate(images):
        cols[idx % 3].image(img, caption=f"出目写真 #{idx+1}", use_container_width=True)
    
    if st.button("設定推測レバーを叩く！ 🎰", type="primary"):
        with st.spinner("出目・物理ファクト・オカルト排除解析中..."):
            try:
                cfg = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    temperature=0.3
                )
                
                prompt_text = f"この商品の設定判別と立ち回りを判定してください。実戦エリアは【{region}】です。"
                if user_memo.strip():
                    prompt_text += f"\n【打手からの実戦メモ・補足情報】: {user_memo.strip()}"
                
                contents_payload = images + [prompt_text]
                
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=contents_payload,
                    config=cfg
                )
                res = json.loads(response.text)
                
                st.subheader(f"🔍 判定台: {res['product_name']}")
                st.caption(f"スペック分類: {res.get('genre', '一般惣菜')} ｜ エリア: {region}")
                
                j = res["slot_judgment"]
                col1, col2 = st.columns(2)
                col1.metric("設定推測", f"設定 {j['setting']}")
                col2.metric("機械割", f"{j['payout_rate']}%")
                
                st.markdown(f"<div class='action-box'><b>🎯 今夜の立ち回り:</b><br>{j['action']}</div>", unsafe_allow_html=True)
                
                t_cls = {
                    "レインボー": "badge-rainbow",
                    "キリン柄": "badge-kirin",
                    "ゴールド": "badge-gold",
                    "シルバー": "badge-silver",
                    "ブロンズ": "badge-bronze"
                }.get(j["trophy"], "badge-none")
                
                st.markdown(f"**トロフィー**: <span class='{t_cls}'>{j['trophy']}</span>", unsafe_allow_html=True)
                st.markdown("---")
                
                p = res["pricing"]
                p1, p2, p3, p4 = st.columns(4)
                p1.write(f"**定価**: ¥{p['list_price']:,}" if p['list_price'] else "**定価**: 不明")
                p2.write(f"**値引き**: {p['discount_type']}")
                p3.write(f"**実支払額**: ¥{p['pay_price']:,}" if p['pay_price'] else "**実支払額**: 不明")
                p4.write(f"**適正価格**: ¥{p['fair_price']:,}")
                st.markdown("---")
                
                f = res["features"]
                icon = a_type_icon if "和食" in res.get('genre', '') or "おこわ" in res.get('genre', '') else "🍱"
                st.markdown(f"#### {icon} 特性 & 盤面チェックポイント")
                st.write(f"- **メイン評価**: {f['core_eval']}")
                pts = f.get("checkpoints", [])
                if pts:
                    st.markdown("**留意点**: " + " ".join([f"<span class='point-chip'>📌 {pt}</span>" for pt in pts]), unsafe_allow_html=True)
                else:
                    st.write("**留意点**: 特になし（良好なノーマル仕様）")
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
