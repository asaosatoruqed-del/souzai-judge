import os
import json
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="惣菜設定判別機", page_icon="🎰", layout="centered")

st.markdown("""
<style>
    /* トロフィーバッジ（名称統一） */
    .badge-rainbow { background: linear-gradient(45deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #8b00ff); color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .badge-kirin { background: #e6b422; color: #000; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .badge-gold { background-color: #ffd700; color: #000; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .badge-silver { background-color: #c0c0c0; color: #000; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .badge-bronze { background-color: #cd7f32; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; }
    .badge-none { background-color: #33333e; color: #888; padding: 4px 10px; border-radius: 4px; }
    
    /* 留意点：落ち着いたダークグレー基調 */
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
    
    /* 立ち回り表示用バナー */
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

# サイドバー設定
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
    "惣菜・弁当の画像およびユーザーの補足テキスト情報から、実質コスパを設定（1〜6）および機械割で判定するパチスロ風エージェントです。\n\n"
    "【ユーザー補足情報の扱い】\n"
    "ユーザーから画像では見えない情報（持った重み、上げ底の深さ、値引きシールの重ね貼り履歴、肉の厚みなど）が提供された場合、"
    "それを『打手からの決定的な小役カウント・実戦データ』として強く判別に反映させてください。\n\n"
    "【立ち回り鉄則】\n"
    "・設定4以上（機械割104%超）: 定価でも迷わず即買い・キープ推奨！設定4確定なら腰を据えてツモるのがプロの鉄則。値引きを待つ必要は一切ない。\n"
    "・設定3以下（機械割101%未満）: 定価ではスルー・即ヤメ推奨。夕方以降の値引きシール（CZ）が付くまで見送り。\n\n"
    "【料理ジャンル別スペック】\n"
    "1.
