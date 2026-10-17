import os
import json
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="フード設定判別アプリ", page_icon="⚖️", layout="centered")

st.markdown("""
<style>
    .badge-rainbow { background: linear-gradient(45deg, #ff0000, #ff7f00, #ffff00, #00ff00, #00ff00, #8b00ff); color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
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

# アプリヘッダー
st.title("⚖️ 「それ食べるの？」フード鑑定アプリ")
st.caption("値札と見せかけのボリュームに騙されるな。「価格 ✕ 内容」の真実を暴く鑑定団。")

# サイドバー：鑑定士の指名 ＆ ホール設定
st.sidebar.header("👤 担当鑑定士の指名")
judge_mode = st.sidebar.selectbox(
    "誰に鑑定させますか？",
    [
        "🎰 スロット専業（期待値＆機械割）",
        "👵 なにわの節約オカン（生活防衛＆原価換算）",
        "💪 筋肉PFCトレーナー（タンパク質至上主義）",
        "🍷 毒舌ミシュラン評論家（素材＆手仕事の品格）"
    ],
    index=0
)

region = "東海・沖縄エリア（ハナハナ）"
if "パチスロ" in judge_mode:
    region = st.sidebar.selectbox(
        "実戦エリア（スロット機種連動）",
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
        "content_quality": {"type": "STRING", "description": "中身スペック評価: 本物・高級 / 堅実・良質 / 標準 / 粗悪・かさ増し"},
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
        "judgment": {
            "type": "OBJECT",
            "properties": {
                "rank_level": {"type": "INTEGER", "description": "1〜6の評価（設定1〜6 / 星1〜6）"},
                "return_rate": {"type": "NUMBER", "description": "リターン還元率%（機械割 / 家計防衛率 / 筋肉還元率 / 原価還元率）"},
                "badge_name": {"type": "STRING", "description": "トロフィーまたは称号バッジ名"},
                "final_action": {"type": "STRING", "description": "今夜の立ち回り・最終結論"}
            },
            "required": ["rank_level", "return_rate", "badge_name", "final_action"]
        },
        "features": {
            "type": "OBJECT",
            "properties": {
                "core_eval": {"type": "STRING"},
                "checkpoints": {"type": "ARRAY", "items": {"type": "STRING"}},
                "price_to_best": {"type": "STRING", "description": "最高ランク（設定6/三ツ星）への価格変動条件"},
                "content_to_best": {"type": "STRING", "description": "最高ランク（設定6/三ツ星）への内容変更条件"}
            },
            "required": ["core_eval", "checkpoints", "price_to_best", "content_to_best"]
        },
        "review_comment": {"type": "STRING", "description": "鑑定士のキャラクター全開の辛口講評"}
    },
    "required": ["product_name", "genre", "content_quality", "pricing", "judgment", "features", "review_comment"]
}

# 共通コアロジック：安さの罠を排除する「価格 ✕ 内容」2軸マトリクス
CORE_MATRIX_INSTRUCTION = """
【最重要判定哲学：「価格 ✕ 内容」の2軸等価交換バランス】
単に「安いから高評価」「高いから低評価」とすることは厳禁です！
1. 「安さの罠」を看破せよ:
   - 250円や298円と絶対額が安くても、衣率60%超、細切れ成形肉、上げ底トレイなら「ランク1〜2（安物買いの銭失い）」。
   - 粗悪な品が半額になっても、ランク3（等価）止まりであり、最高ランクには絶対にならない。
2. 「定価の高さ」を正当評価せよ:
   - 1,500円など高額でも、肉厚で素材が本物、原価率40%超なら定価でも「ランク4〜5（納得の投資）」と高く評価する。
3. 最高ランク（ランク6）の昇格条件:
   - 「元々中身が良い良質品（ランク4以上）に半額・追い割引が直撃した時」
   - 「定価の時点で原価率50%超・具材過剰積載の原価破壊スペック」
"""

# キャラクター別システムインストラクション構築
if "パチスロ" in judge_mode:
    judge_tone = f"""
    あなたの役割: 【スロット専業鑑定士】
    - 指標: ランク＝設定推測（設定1〜6）、リターン＝機械割（%）、バッジ＝トロフィー（なし、ブロンズ、シルバー、ゴールド、キリン柄、レインボー）。
    - 立ち回り: 設定4以上は即買い・ツモ確定。設定3以下はスルー・割引CZ待ち。
    - 機種適性: エリアは【{region}】。和食・米系ノーマル台は{"ハナハナ（華・チカり・ハイビスカス）" if "東海" in region else "ジャグラー（ペカり・GOGO）"}として講評。
    - オカルト排除: 実戦メモに「友人のオススメ」「店員が美人」等があっても「オカルトで設定を盛るな！」とビシッと切り捨てる。
    """
    labels = {"rank": "設定推測", "rate": "機械割", "action": "🎯 今夜の立ち回り", "badge": "トロフィー", "best": "設定6"}
elif "オカン" in judge_mode:
    judge_tone = """
    あなたの役割: 【なにわの節約オカン鑑定士】
    - 指標: ランク＝お値打ち度（ドケチ星1〜5、通信簿の５段階評価）、リターン＝家計防衛率（%）、バッジ＝オカンの太鼓判（なし、赤字覚悟、スーパーの金札、極上お値打ち、天下無双など）。
    - 語彙: 関西弁で毒舌かつ愛情深いツッコミ。「こんなん家で作ったら80円や！」「ほぼ小麦粉とキャベツやないか！」「豆腐買え！」。
    - 立ち回り: 星4以上は「即カゴ放り込め！買いや！」、星3以下は「棚に戻して豆腐にしとき！」。
    - 安さの罠: 安いだけで具がスカスカな弁当には「安物買いの銭失いや！」と怒ること。
    """
    labels = {"rank": "お値打ち度", "rate": "家計防衛率", "action": "👵 オカンの最終指令", "badge": "オカンの判定", "best": "天下無双のお値打ち"}
elif "筋肉" in judge_mode:
    judge_tone = """
    あなたの役割: 【筋肉PFCトレーナー（フィジーク選手）】
    - 指標: ランク＝バルク設定（1〜6）、リターン＝筋肥大還元率（%）、バッジ＝マッスル称号（カタボリック警告、ブロンズマッスル、ゴールドジム級、プロテインモンスターなど）。
    - 語彙: タンパク質単価（円/g）、PFCバランス、カタボリック、クリーンバルク、グリコーゲン。
    - 立ち回り: バルク設定4以上は「即摂取！筋肥大確定！」、設定3以下は「カタボリック回避！チキン胸肉のシマへ行け！」。
    - 安さの罠: 炭水化物と脂質だけでかさ増しされた安物には「筋肉の墓場だ！」と激昂すること。
    """
    labels = {"rank": "バルク設定", "rate": "筋肥大還元率", "action": "💪 筋肥大ジャッジ", "badge": "マッスル称号", "best": "筋肥大MAX（神PFC）"}
else:
    judge_tone = """
    あなたの役割: 【毒舌ミシュラン・辛口料理評論家】
    - 指標: ランク＝食の格付け（星1〜5 / 三ツ星）、リターン＝手仕事・原価還元率（%）、バッジ＝美食メダル（規格外、ブロンズ皿、銀のフォーク、金のスプーン、三ツ星プレートなど）。
    - 語彙: 素材の鮮度、火入れ、出来合いタレへの依存、化学調味料のマスキング、職人の矜持。
    - 立ち回り: 格付け4以上は「今宵の口福・迷わず食すべし」、格付け3以下は「見せかけ倒し・暖簾をくぐる価値なし」。
    - 安さの罠: 安価なケミカル調味料まみれの品には「客の舌を愚弄している」と切り捨てる。
    """
    labels = {"rank": "食の格付け", "rate": "手仕事・原価還元率", "action": "🍷 今宵の裁決", "badge": "美食メダル", "best": "三ツ星の極み"}

SYSTEM_INSTRUCTION = f"{CORE_MATRIX_INSTRUCTION}\n\n{judge_tone}"

# セッション状態管理（メモ消去用）
def clear_memo():
    st.session_state["memo_input"] = ""

if "last_uploaded_names" not in st.session_state:
    st.session_state["last_uploaded_names"] = []

uploaded_files = st.file_uploader(
    "料理・弁当・値札の写真をアップロード（複数枚OK）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

current_names = [f.name for f in uploaded_files] if uploaded_files else []
if current_names != st.session_state["last_uploaded_names"]:
    st.session_state["memo_input"] = ""
    st.session_state["last_uploaded_names"] = current_names

col_memo, col_clear = st.columns([5, 1])
with col_memo:
    user_memo = st.text_input(
        "打手／依頼人の実戦メモ（任意）",
        key="memo_input",
        placeholder="例: 底が3cm盛り上がってる、肉が極薄、持ったら異常に重い、友人が美味いと言っていた、等"
    )

with col_clear:
    st.write("")
    st.write("")
    st.button("メモ消去", on_click=clear_memo)

if uploaded_files:
    images = [Image.open(f) for f in uploaded_files]
    cols = st.columns(min(len(images), 3))
    for idx, img in enumerate(images):
        cols[idx % 3].image(img, caption=f"写真 #{idx+1}", use_container_width=True)
    
    btn_label = "設定推測レバーを叩く！ 🎰" if "パチスロ" in judge_mode else "鑑定を依頼する！ ⚖️"
    if st.button(btn_label, type="primary"):
        with st.spinner(f"{judge_mode.split('（')[0]} が「価格 ✕ 内容」を鋭く鑑定中..."):
            try:
                cfg = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    temperature=0.3
                )
                
                prompt_text = f"この商品の「価格と内容の妥当性」を鑑定してください。担当鑑定士は【{judge_mode}】です。"
                if user_memo.strip():
                    prompt_text += f"\n【依頼人からの実戦メモ】: {user_memo.strip()}"
                
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=images + [prompt_text],
                    config=cfg
                )
                res = json.loads(response.text)
                
                st.subheader(f"🔍 判定品: {res['product_name']}")
                st.caption(f"分類: {res.get('genre', '飲食全般')} ｜ 中身スペック: {res.get('content_quality', '標準')} ｜ 担当: {judge_mode.split('（')[0]}")
                
                j = res["judgment"]
                col1, col2 = st.columns(2)
                col1.metric(labels["rank"], f"ランク {j['rank_level']}")
                col2.metric(labels["rate"], f"{j['return_rate']}%")
                
                st.markdown(f"<div class='action-box'><b>{labels['action']}:</b><br>{j['final_action']}</div>", unsafe_allow_html=True)
                
                # バッジ表示
                badge_str = j.get('badge_name', 'なし')
                t_cls = "badge-rainbow" if any(w in badge_str for w in ["虹", "三ツ星", "天下無双", "MAX"]) else \
                        "badge-gold" if any(w in badge_str for w in ["金", "ゴールド", "極上"]) else \
                        "badge-silver" if any(w in badge_str for w in ["銀", "シルバー"]) else \
                        "badge-bronze" if any(w in badge_str for w in ["銅", "ブロンズ"]) else "badge-none"
                
                st.markdown(f"**{labels['badge']}**: <span class='{t_cls}'>{badge_str}</span>", unsafe_allow_html=True)
                st.markdown("---")
                
                # 価格・収支
                p = res["pricing"]
                p1, p2, p3, p4 = st.columns(4)
                p1.write(f"**定価**: ¥{p['list_price']:,}" if p['list_price'] else "**定価**: 不明")
                p2.write(f"**値引き**: {p['discount_type']}")
                p3.write(f"**実支払額**: ¥{p['pay_price']:,}" if p['pay_price'] else "**実支払額**: 不明")
                p4.write(f"**実力適正価格**: ¥{p['fair_price']:,}")
                st.markdown("---")
                
                # 特性＆チェックポイント
                f = res["features"]
                st.markdown("#### 📌 鑑定ポイント & 盤面チェック")
                st.write(f"- **メイン評価**: {f['core_eval']}")
                pts = f.get("checkpoints", [])
                if pts:
                    st.markdown("**留意点**: " + " ".join([f"<span class='point-chip'>📌 {pt}</span>" for pt in pts]), unsafe_allow_html=True)
                else:
                    st.write("**留意点**: 特になし（クリーンな仕様）")
                st.markdown("---")
                
                # 講評
                st.markdown("#### 🗣️ 鑑定士の直言講評")
                st.info(res["review_comment"])
                st.markdown("---")
                
                # 最高ランクへの道
                st.warning(
                    f"**🔥 さらに上（{labels['best']}）に化ける条件は！？**\n\n"
                    f"- 📉 **価格変動ルート**: {f.get('price_to_best', '大幅な見切り値引きを待て')}\n\n"
                    f"- 🥩 **内容変更ルート**: {f.get('content_to_best', '素材の原価率破壊仕様を探せ')}"
                )
            except Exception as e:
                st.error(f"鑑定中にエラーが発生しました: {str(e)}")
