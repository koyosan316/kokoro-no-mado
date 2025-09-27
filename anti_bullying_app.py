# anti_bullying_app.py
# -*- coding: utf-8 -*-

from datetime import datetime
from pathlib import Path
import csv
import re
import urllib.parse
import streamlit as st
import time


# ================= 基本設定 =================
st.set_page_config(page_title="こころのまど", page_icon="💬", layout="wide")

PRIMARY = "#2563eb"
ACCENT = "#10b981"
DANGER = "#ef4444"
CSS = f"""
<style>
:root {{
  --primary: {PRIMARY};
  --accent: {ACCENT};
  --danger: {DANGER};
}}
.main-title {{ font-size: 28px; font-weight: 800; margin-bottom: .2rem; }}
.subtitle {{ color:#666; margin-bottom: 1rem; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:999px; background:var(--accent); color:white; font-size:12px; margin-right:6px; }}
.card {{ border:1px solid #eee; border-radius:16px; padding:16px; margin-bottom:12px; }}
.alert {{ border:1px solid #fecaca; background:#fee2e2; color:#7f1d1d; border-radius:12px; padding:12px; }}
.small-muted {{ color:#777; font-size:12px; }}
.helpbtn a {{
  display:inline-block; background:var(--primary); color:white; padding:10px 14px; border-radius:10px; text-decoration:none;
}}
.exit a {{
  display:inline-block; background:#6b7280; color:white; padding:8px 12px; border-radius:10px; text-decoration:none; font-size:12px;
}}
.btnlink a {{
  display:inline-block; background:#111827; color:white; padding:8px 12px; border-radius:10px; text-decoration:none; font-size:13px;
}}
.kv {{ margin: 6px 0; }}
.kv b {{ display:inline-block; min-width: 9em; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
# ==== 状態の初期化（最上部で一度）====
def init_state():
    defaults = {
        "menu": "ホーム",
        "breathe_pre_text": "",
        "breathe_post_text": "",
        "breathe_pre_score": 3,
        "breathe_post_score": 3,
        # 将来AIチャットを戻す時はここに "chat" や "prefill" も追加
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

init_state()

# ================= データ保存（体験用） =================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
REPORT_CSV = DATA_DIR / "reports.csv"
if not REPORT_CSV.exists():
    with REPORT_CSV.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp_iso", "who", "where", "what", "risk"])

# ================= ヘッダー =================
colL, colR = st.columns([5,2])
with colL:
    st.markdown('<div class="main-title">💬 こころのまど</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">安心して話せる、ひとりじゃない場所。</div>', unsafe_allow_html=True)
with colR:
    st.markdown(
        """
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          <a target="_blank" href="https://www.mext.go.jp/a_menu/shotou/seitoshidou/06112210.htm"
             style="flex:1; text-align:center; background:#2563eb; color:white; 
                    padding:6px 10px; border-radius:8px; text-decoration:none; font-size:12px;">
             📖 子ども向け
          </a>
          <a target="_blank" href="https://www.mhlw.go.jp/mamorouyokokoro/soudan/tel/"
             style="flex:1; text-align:center; background:#10b981; color:white; 
                    padding:6px 10px; border-radius:8px; text-decoration:none; font-size:12px;">
             🧭 全年齢向け
          </a>
        </div>
        <div style="margin-top:6px;">
          <a target="_blank" href="https://www.google.com"
             style="display:inline-block; background:#6b7280; color:white;
                    padding:6px 10px; border-radius:8px; font-size:12px; text-decoration:none;">
             緊急離脱
          </a>
        </div>
        """,
        unsafe_allow_html=True
    )


# CSS（CSS = f"""..."""; st.markdown(CSS, ...)）の少し下に関数定義
def reset_dark_css_if_needed(current_page: str):
    if current_page != "深呼吸":
        st.markdown("""
        <style>
        .stApp { background: #ffffff !important; }
        .block-container { color: inherit; }
        </style>
        """, unsafe_allow_html=True)

# ================= ページ切り替え =================
with st.sidebar:
    # 目立つ見出し
    st.markdown(
        "<div style='font-weight:800; font-size:18px; margin-bottom:6px;'>📂 メニュー</div>",
        unsafe_allow_html=True
    )
    st.caption("ページを選んでください")

    # ラジオにもラベルを出して「選択欄」だと明示
    page = st.radio(
        "メニュー",
        ["ホーム", "深呼吸", "整理フォーム（匿名）", "セルフチェック", "学ぶ", "クイズ", "相談窓口（地域別）"],
        index=0,
        key="menu",
        label_visibility="visible"
    )

    # --- フィードバックボタン（常に表示） ---
    st.markdown(
        """
        <div style="margin-top:10px; text-align:center;">
          <a target="_blank" href="https://forms.gle/PzW6mZFXtUJW3UZSA"
             style="display:inline-block;
                    background-color:#2563eb; color:white;
                    padding:6px 10px; border-radius:6px;
                    text-decoration:none; font-size:12px;">
             📝 フィードバック
          </a>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.warning("⚠️ ※このサイトは試験的に公開しています。深刻な場合は専門窓口や医療機関へご相談ください。")


# ================= 危険度チェック =================
RISK_KEYWORDS = [
    r"死にたい", r"消えたい", r"自殺",
    r"殺(す|され)", r"殴(ら|られ)", r"蹴(ら|られ)", r"暴力",
    r"家に帰りたくない", r"監禁", r"脅(さ|され|迫)",
    r"裸|性的|はだか", r"写真.*拡散", r"晒(し|され)"
]
# 既存のRISK_KEYWORDSの直後に追加
RISK_PATTERNS = [re.compile(p, re.IGNORECASE) for p in RISK_KEYWORDS]

# 既存のdetect_riskをこの実装に差し替え
def detect_risk(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return any(p.search(t) for p in RISK_PATTERNS)


def risk_banner():
    st.markdown(
        """
<div class="alert">
<strong>⚠️ いま危険かも。</strong><br>
安全が少しでも心配なら、いますぐ周囲の人に助けを求める・110番・189へ。オンライン上のことでも相談可能です。<br>
<span class="small-muted">※ このアプリは緊急通報を代行できません。</span>
</div>
""",
        unsafe_allow_html=True,
    )

# ================= ルールベース簡易ボット =================
def bot_reply(user_text: str) -> str:
    t = (user_text or "").strip()
    if detect_risk(t):
        return (
            "いま話してくれてありがとう。安全が少しでも心配なら、周囲の人・110・189へ連絡してね。"
            "ここでは一緒に状況を整理しよう。『いつ・どこで・だれが・何を・その後どうなった』を書ける範囲で教えてくれる？"
        )
    if re.search(r"無視|ハブ|仲間外れ|既読スルー", t):
        return (
            "無視や仲間外れはつらいよね。まずは①事実の記録（日時/人/場所）②信頼できる人への共有③ひとりにならない工夫、が大切。"
            "最近あった場面を一つ、書ける範囲で教えてもらえる？"
        )
    if re.search(r"悪口|からか|罵倒|暴言", t):
        return (
            "言葉のいじめは心に残るよね。記録は“広めずに”保管して、直接の応酬は避けて相談先へ繋ごう。"
            "相手の発言内容や状況を、覚えている範囲で教えてね。"
        )
    if re.search(r"晒|拡散|なりすまし|画像|動画|SNS|X|インスタ|tiktok|ディスコ", t, re.I):
        return (
            "ネットいじめは早めの対処が大切。スクショで記録→プラットフォーム通報→相談先に共有、の順がおすすめ。"
            "URLやIDはここには貼らず、状況だけ教えてね。"
        )
    if re.search(r"殴|蹴|暴力|物.*壊|取(られ|り上げ)", t):
        return (
            "身体的な危険があるかもしれない。安全確保が最優先。今その場を離れられる？"
            "可能なら周りの人に助けを求めて、あとから記録を残そう。怪我はない？"
        )
    return (
        "話してくれてありがとう。まずは状況を一緒に整理しよう。"
        "『いつ』『どこで』『だれが』『何をした/言った』『その後どうなった』を、書ける範囲で教えてね。"
    )
# ================= ページ：ホーム =================
if page == "ホーム":
    st.markdown("## 🏠 ホーム")
    st.markdown("### ようこそ *こころのまど* へ")
    st.markdown("安心できる場所をめざしてテスト公開しています。")
    st.markdown("---")
    st.markdown(
        "<div style='padding:20px; background:#fee2e2; color:#991b1b; border-radius:12px; font-size:20px; font-weight:bold; text-align:center;'>"
        "⚠️ ※このサイトは試験的に公開しています。深刻な場合は専門窓口や医療機関へご相談ください。"
        "</div>",
        unsafe_allow_html=True
    )
    st.write("""
ここは、安心して **心の中を整理したり、学んだり、助けを探したりできる案内板** です。  

- つらいときは、ここに来てまず深呼吸してもいい
- 言葉にしづらい気持ちは、整理フォームに書き出してもいい  
- 知識をつけて自分や誰かを守るために学んでもいい  
- すぐ助けが必要なときは、相談窓口を開いてみて  
""")

    st.divider()

    st.markdown("### 🌿 このサイトでできること")
    st.markdown("""
- 🌌 **深呼吸モード** → 不安や緊張を落ち着けたいとき  
- 📝 **整理フォーム** → 状況を文章に整理したいとき  
- 📒 **セルフチェック** → ストレスやトラウマ反応をチェックしたいとき  
- 📚 **学ぶ** → いじめや不安の対処法を知りたいとき  
- ❓ **クイズ** → 遊びながら対応方法を学びたいとき  
- 📞 **相談窓口** → 電話番号や公式ページをすぐ探したいとき  
""")

    st.info("💡 ここで見たり書いたりすることは、あなたを守るためのものです。")
    st.caption("※ 個人情報は書かないでください。このサイトは安心のための学習用MVPです。")

# ================= ページ：深呼吸モード（黒背景・3サイクル） =================
if page == "深呼吸":
    # このページだけ黒背景にするCSS
    DARK_CSS = """
    <style>
    .stApp { background:#0b0f1a !important; }
    .block-container { color:#e5e7eb; }
    .breathe-circle {
        width: 180px; height: 180px; border-radius: 9999px;
        margin: 24px auto; background: radial-gradient(circle at 30% 30%, #ffffffaa, #ffffff22);
        transform: scale(0.8); transition: transform 0.9s ease-in-out;
        box-shadow: 0 0 40px #ffffff22, 0 0 8px #ffffff33 inset;
    }
    .breathe-text { text-align:center; font-size: 28px; font-weight: 700; letter-spacing: .12em; }
    .caption-center { text-align:center; color:#cbd5e1; }
    .card-dark { background:#111827; border:1px solid #1f2937; border-radius:16px; padding:16px; color:#e5e7eb; }
    .score-circles { text-align:center; font-size: 24px; letter-spacing: .2em; }
    a { color:#93c5fd !important; }
    </style>
    """
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align:center;margin:0;'>🌌 深呼吸モード</h2>", unsafe_allow_html=True)
    st.markdown("<p class='caption-center'>3回だけ、一緒にゆっくり。ここではあなたのペースが正解です。</p>", unsafe_allow_html=True)

    # 事前メモとスコア
    col_preL, col_preR = st.columns([2,1])
    with col_preL:
        pre_text = st.text_input("いまの気分（ひとこと）", placeholder="例）胸がドキドキする / ざわざわする など", key="breathe_pre_text")
    with col_preR:
        pre_score = st.slider("いまのつらさ", 1, 5, 3, key="breathe_pre_score")
        st.caption("1=軽い  5=とてもつらい")

    # 呼吸アニメーション（3サイクル）
    start = st.button("▶ 3回はじめる", type="primary", use_container_width=True)

    circle_ph = st.empty()
    text_ph = st.empty()

    def draw_circles(n: int) -> str:
        # 1〜5 を ●○ で可視化
        n = max(0, min(5, n))
        return " ".join(["●"]*n + ["○"]*(5-n))

    if start:
        # 3サイクル（吸って4秒→吐いて8秒）
        cycles = 3
        for i in range(cycles):
            # 各サイクルの冒頭に追加（任意）
            st.toast(f"{i+1}/{cycles} 回目", icon="⏳")

            # 吸う
            circle_ph.markdown("<div class='breathe-circle' style='transform:scale(1.05);'></div>", unsafe_allow_html=True)
            text_ph.markdown("<div class='breathe-text'> 鼻で吸って…</div>", unsafe_allow_html=True)
            time.sleep(4)

            # 止める（7秒）
            circle_ph.markdown("<div class='breathe-circle' style='transform:scale(1.05);'></div>", unsafe_allow_html=True)
            text_ph.markdown("<div class='breathe-text'> 息を止めて…</div>", unsafe_allow_html=True)
            time.sleep(7)

            # 吐く
            circle_ph.markdown("<div class='breathe-circle' style='transform:scale(0.8);'></div>", unsafe_allow_html=True)
            text_ph.markdown("<div class='breathe-text'> 口で吐いて…</div>", unsafe_allow_html=True)
            time.sleep(8)

        # 終了表示
        text_ph.markdown("<div class='breathe-text'>おつかれさま。ゆっくりできた？</div>", unsafe_allow_html=True)
        # 呼吸法の説明
        st.markdown("### 🧘‍♀️ 今やった呼吸法について")
        st.info( 
    "「4-7-8 呼吸法」は、4秒で鼻から吸い、7秒息を止めて、8秒かけて口から吐く呼吸法です。"
    "リラックス効果が高く、不安や緊張をやわらげたり、寝る前に気持ちを落ち着けるのに使われます。"
    "医学博士アンドルー・ワイルによって広められた方法で、繰り返すほど深いリラックスを得られるとされています。"
    "今の気持ちを書いて、結果をまとめてみてみてください"
)

    st.markdown("---")

    # 事後メモと比較
    col_postL, col_postR = st.columns([2,1])
    with col_postL:
        post_text = st.text_input("深呼吸のあと（ひとこと）", placeholder="例）少し落ち着いた / まだ不安がある など", key="breathe_post_text")
    with col_postR:
        post_score = st.slider("いまのつらさ（深呼吸のあと）", 1, 5, 3, key="breathe_post_score")
        st.caption("1=軽い  5=とてもつらい")

    if st.button("結果をまとめる", use_container_width=True):
        diff = pre_score - post_score  # +なら軽くなった
        change_txt = "少し軽くなったかも" if diff >= 1 else ("変わらない/わからない" if diff == 0 else "少し重くなったかも")
        with st.container():
            st.markdown("<div class='card-dark'>", unsafe_allow_html=True)
            st.markdown("**〇で可視化（●=つらさ）**", unsafe_allow_html=True)
            st.markdown(
                f"<div class='score-circles'>前：{draw_circles(pre_score)}　→　後：{draw_circles(post_score)}</div>",
                unsafe_allow_html=True
            )
            st.markdown("**ひとことメモ**", unsafe_allow_html=True)
            st.write(f"前：{pre_text or '（未入力）'}")
            st.write(f"後：{post_text or '（未入力）'}")
            st.write(f"**変化**：{change_txt}（{pre_score} → {post_score}）")
            st.markdown("</div>", unsafe_allow_html=True)

        # 小さなメモをダウンロード
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        memo = (
            f"[深呼吸モード] {timestamp}\n"
            f"前の気分：{pre_text or '（未入力）'} / つらさ：{pre_score}\n"
            f"後の気分：{post_text or '（未入力）'} / つらさ：{post_score}\n"
            f"メモ：{change_txt}\n"
        )
        st.download_button("📝 この結果を保存（TXT）", data=memo, file_name=f"breathe_{timestamp}.txt", mime="text/plain", use_container_width=True)

    st.caption("※ このページは記録をサーバーに送信しません。あなたの端末だけで動きます。")

# ================= ページ：AIチャット相談 =================
if page == "AIチャット相談":
    st.markdown("### AIチャット相談")
    st.caption("※ 個人が特定できる情報（実名/住所/ID/URLなど）は書かないでね。")

    if "chat" not in st.session_state:
        st.session_state.chat = [
            {"role": "assistant", "content": "こんにちは。ここは安心して話せる場所です。今どんな状況？"}
        ]

    with st.container(border=True):
        st.write("🧭 話題の例（クリックで入力）：")
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("無視される/外される"):
            st.session_state.prefill = "クラス/職場で無視されます。どうしたらいい？"
        if c2.button("悪口/からかわれる"):
            st.session_state.prefill = "SNSと対面で悪口を言われています。"
        if c3.button("ネットで晒される"):
            st.session_state.prefill = "Xで写真を晒されました。どうすれば？"
        if c4.button("暴力の不安"):
            st.session_state.prefill = "叩かれそうで怖いです。"

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_msg = st.chat_input("ここに入力してね")
    if "prefill" in st.session_state and st.session_state.prefill:
        user_msg = st.session_state.prefill
        st.session_state.prefill = ""

    if user_msg:
        st.session_state.chat.append({"role": "user", "content": user_msg})
        reply = bot_reply(user_msg)
        st.session_state.chat.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            if detect_risk(user_msg):
                risk_banner()
            st.write(reply)

    colA, colB = st.columns([1,2])
    if colA.button("🧹 会話をリセット", use_container_width=True):
        st.session_state.chat = [
            {"role": "assistant", "content": "こんにちは。ここは安心して話せる場所です。今どんな状況？"}
        ]
        st.rerun()

    def export_chat_to_csv():
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        p = DATA_DIR / f"chat_{ts}.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["role", "content"])
            for m in st.session_state.chat:
                w.writerow([m["role"], m["content"]])
        return p

    if colB.button("💾 会話をCSV保存", use_container_width=True):
        path = export_chat_to_csv()
        st.success(f"保存しました：{path}")

# ================= ページ：整理フォーム（匿名） =================
elif page == "整理フォーム（匿名）":
    st.markdown("### 悩みを整理するフォーム（匿名）")
    st.caption("※ 個人が特定できる情報（実名・住所・アカウントID・URLなど）は書かないでね。")

    # ---- 選択肢（未選択時プレースホルダーを日本語に）----
    role = st.radio(
        "あなたの立場",
        ["被害を受けている（かもしれない）", "いじめてしまっている（かもしれない）", "目撃した"],
        index=0
    )
    age = st.selectbox(
        "あなたの年齢層",
        ["小学生", "中学生", "高校生", "大学生/専門", "大人/社会人", "不明"],
        index=None, placeholder="選んでください"
    )
    when_start = st.selectbox(
        "いつから？",
        ["今日", "昨日", "先週から", "数週間前から", "数か月前から", "1年以上前から", "不明"],
        index=None, placeholder="選んでください"
    )
    freq = st.selectbox(
        "どのくらいの頻度？",
        ["一度だけ", "ときどき", "ほぼ毎日", "不明"],
        index=None, placeholder="選んでください"
    )
    where = st.selectbox(
        "どこで？",
        ["学校", "部活/サークル", "職場/バイト", "家・近所", "オンライン(SNS/ゲーム/DM)", "その他/不明"],
        index=None, placeholder="選んでください"
    )

    st.markdown("#### 登場人物（具体名は書かない）")
    victim = st.text_input("誰が（被害者側）？", value="自分")
    offender = st.text_input("誰が（加害者側）？", value="不明")
    n_people = st.selectbox(
        "加害側の人数",
        ["1人", "2〜3人", "4人以上", "不明"],
        index=None, placeholder="選んでください"
    )

    what = st.multiselect(
        "何があった？（複数可）",
        [
            "悪口・からかい・ひどいあだ名で呼ばれる",
            "無視・仲間外れ・連絡から外される",
            "持ち物を隠される/壊される/取られる",
            "叩く/蹴る/物を投げられるなどの暴力",
            "ネットで晒される/なりすまし/拡散される",
            "不適切な画像/動画を送られる・送ってしまう",
            "しつこい要求/脅し/誘導",
            "その他（自由入力で補足）",
        ],
        placeholder="当てはまるものを選んでください"
    )
    what_free = st.text_area("上にないこと・補足（具体名・URLは書かない）", height=100, placeholder="書ける範囲でOK")

    feelings = st.multiselect(
        "そのときの気持ち（複数可）",
        ["悲しい", "怖い", "不安", "怒り", "恥ずかしい", "動揺した", "つらい", "無感覚", "分からない"],
        placeholder="当てはまるものを選んでください"
    )
    impact = st.multiselect(
        "影響（複数可）",
        ["学業/仕事に支障", "欠席・遅刻が増えた", "体調不良", "人間関係が不安", "外出やSNSが怖い", "その他/不明"],
        placeholder="当てはまるものを選んでください"
    )
    wish = st.selectbox(
        "今の希望",
        ["まず整理したい", "アドバイスが欲しい", "専門窓口に繋がりたい", "分からない/未定"],
        index=None, placeholder="選んでください"
    )

    # ---- 立場別の自由記入 ----
    if role == "いじめてしまっている（かもしれない）":
        st.info("※「相手が嫌がっているかも」と感じたら、まずは距離を置いて専門家の助言を。")
        self_reflect = st.text_area("何をしてしまったか・理由だと思うこと（書ける範囲で）", height=100, placeholder="書ける範囲でOK")
    elif role == "目撃した":
        self_reflect = st.text_area("見た/聞いた内容（日時・場所・様子など、書ける範囲で）", height=100, placeholder="例：○月○日○時ごろ、昇降口で…")
    else:
        self_reflect = st.text_area("詳細（いつ/どこ/だれ/何を/その後どうなった、を書ける範囲で）", height=100, placeholder="例：先週の月曜、教室で…")

    # ---- 必須の選択が未入力なら注意（押しても生成しない）----
    missing = []
    for label, val in [
        ("年齢層", age), ("開始時期", when_start), ("頻度", freq), ("場所", where), ("加害側の人数", n_people), ("今の希望", wish)
    ]:
        if val is None:
            missing.append(label)

    if st.button("整理文をつくる", type="primary", use_container_width=True):
        if missing:
            st.warning("未選択の項目があります：" + "、".join(missing))
        else:
            what_text = "、".join(what) if what else "不明"
            feelings_text = "、".join(feelings) if feelings else "（未記入）"
            impact_text = "、".join(impact) if impact else "（未記入）"

            if role == "被害を受けている（かもしれない）":
                role_line = f"私は{age}です。{when_start}から{freq}、{where}で{offender}（{n_people}）に、{what_text}ことが続いています。"
            elif role == "いじめてしまっている（かもしれない）":
                role_line = f"私は{age}です。{when_start}から{freq}、{where}で{victim}に対して、{what_text}行為をしてしまっている可能性があります。"
            else:
                role_line = f"私は{age}です。{when_start}から{freq}、{where}で、{offender}（{n_people}）が{victim}に対して{what_text}様子を目撃しました。"

            detail_line = f"詳細：{self_reflect.strip()}" if self_reflect.strip() else ""
            feelings_line = f"そのときの気持ち：{feelings_text}。影響：{impact_text}。"
            wish_line = f"現在の希望：{wish}。"
            caution_line = "※この文書には個人が特定できる情報を含めていません。"

            sentence = "\n".join([role_line, detail_line, feelings_line, wish_line, caution_line]).strip()

            st.success("整理された文章（相談で見せられるメモ）")
            st.write(sentence)

            with REPORT_CSV.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([datetime.utcnow().isoformat(), role, where, sentence, "（整理文）"])

            st.download_button(
                label="📝 この整理文をテキストで保存",
                data=sentence,
                file_name=f"seiri_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    # ---- 危険度チェック（自由記入も合わせて判定）----
    joined_text = " ".join([what_free, self_reflect]) if 'self_reflect' in locals() else what_free
    if detect_risk((joined_text or "")):
        risk_banner()
        MHLW_URL = "https://www.mhlw.go.jp/mamorouyokokoro/soudan/tel/"
        st.markdown(
            f"""
            <div style="margin-top:12px;">
              <a href="{MHLW_URL}" target="_blank"
                 style="display:block;text-align:center;
                        background-color:#2563eb; color:white;
                        padding:12px 16px; border-radius:10px;
                        text-decoration:none; font-weight:600;
                        font-size:16px; box-shadow:0 2px 6px rgba(0,0,0,0.2);">
                 🧭 相談してみる（公式窓口へ）
              </a>
            </div>
            """,
            unsafe_allow_html=True
        )


# ================= ページ：学ぶ =================
elif page == "学ぶ":
    st.markdown("## 学ぶコーナー")
    st.markdown("いじめは子どもだけの問題じゃなく、あらゆる年齢や場所で起こり得ます。立場ごとに学んでみよう。")
   

    with st.expander("🔵 自分がいじめられていると感じたら"):
        st.markdown("""
- 気持ちを無理に隠さなくていい  
- 事実をメモやスクショで記録（広めず保管）  
- 信頼できる人・窓口・サービスに共有  
- 「相談＝弱さ」ではなく「自分を守る行動」
        """)

    with st.expander("🟢 誰かがいじめられているのを見たら"):
        st.markdown("""
- 見て見ぬふりは加担になることも  
- 一人で止めようとせず、安全を優先  
- できること：周囲に知らせる／窓口に伝える／一緒にいる
        """)

    with st.expander("🟡 自分がいじめてしまっているかも？と思ったら"):
        st.markdown("""
- 冗談でも相手に傷を残すことがある  
- 相手の反応を思い出す（笑ってなかった？嫌そうだった？）  
- 「ごめん」と伝えるのも勇気  
- 習慣的なからかいに注意
        """)

    with st.expander("🟠 相談するのに勇気がいるとき"):
        st.markdown("""
- 「話す＝弱い」ではなく「守るための行動」  
- 直接言うのが難しいときは匿名フォームやSOSダイヤルを使う  
- メッセージだけ残す仕組みを活用  
- 信頼できる人に「一緒に話して」とお願いするのもOK
        """)

    with st.expander("⚪ 広げないためにできること"):
        st.markdown("""
- 噂を広めない  
- 晒し・拡散に参加しない  
- 加害側のチャットに入らない  
- 小さな「やめようよ」で空気が変わる
        """)

    with st.expander("🟦 いじめについて"):
        st.markdown("""
- **言葉の攻撃**：悪口・からかい・あだ名付け  
- **排除**：無視・仲間外れ・グループから外す  
- **ネット**：晒し・拡散・なりすまし・不適切画像  
- **身体・物**：叩く・蹴る・物を壊す・隠す
        """)

    with st.expander("🟩 ハラスメントについて"):
        st.markdown("""
- **パワハラ**：職場で立場を利用した嫌がらせ  
- **セクハラ**：性的な言動や不適切な接触・画像送信  
- **モラハラ**：精神的支配・侮辱・過度な束縛  
- **ネットハラスメント**：SNSや掲示板での中傷や拡散
        """)

    with st.expander("🟨 不安について"):
        st.markdown("""
- 将来への不安（進学・就職・収入）  
- 人間関係の不安（孤独・信頼関係）  
- 健康や病気の不安（体調・心の不調）  
- 社会的要因（差別・災害・事件報道）
""")
        st.info("※ 不安が続くときは専門家のサポートを受けることも大切です。")

    with st.expander("🟧 対処とセルフケア"):
        st.markdown("""
- 深呼吸・睡眠・食事を整える  
- 感情をノートに書き出す  
- 信頼できる人に「一言だけ話す」  
- 匿名相談や窓口を利用する
        """)

    with st.expander("⚖️ 法律と権利"):
        st.markdown("""
- **いじめ防止対策推進法**：学校はいじめ防止の責任を負う  
- **労働安全衛生法**：職場のパワハラ対策が義務化  
- **男女雇用機会均等法**：セクハラ防止が義務  
- **人権相談窓口**：法務局や弁護士会も相談可能
        """)


# ================= ページ：クイズ（完全ランダム・固定表示・解説） =================
elif page == "クイズ":
    import random

    st.markdown("### いじめ対応クイズ（全8問）")
    st.caption("選択肢と正解の位置はランダムです。途中で並びが変わらないよう固定しています。")

    # ---- 問題定義（正解はテキストで保持）----
    QUESTIONS = [
        {"q":"SNSで友人の写真が晒された。最も適切な対応は？",
         "options":["拡散せず証拠を記録→相談","反論投稿で止める","DMで削除要求","放置"],
         "answer_text":"拡散せず証拠を記録→相談",
         "explain":"拡散せず証拠保存＋相談が鉄則。反論や要求は逆効果になりやすい。"},
        {"q":"グループから外された人がいる。あなたの第一歩は？",
         "options":["声をかけて一緒に過ごす＋相談","見て見ぬふり","加害側に直接抗議","加害側を外す"],
         "answer_text":"声をかけて一緒に過ごす＋相談",
         "explain":"孤立を防ぎ、状況を共有して相談先に繋ぐのが大切。"},
        {"q":"部活/職場で物を隠された。どうする？",
         "options":["やり返す","証拠を残して報告","我慢する","第三者に仕返し依頼"],
         "answer_text":"証拠を残して報告",
         "explain":"仕返しは危険。証拠を記録して組織の窓口に報告が安全。"},
        {"q":"SNSで悪口が広まった。最初にすべきことは？",
         "options":["スクショで記録→相談","本人に直接抗議","拡散を止めるためシェア","自分も書く"],
         "answer_text":"スクショで記録→相談",
         "explain":"まずは記録と相談。感情的な応酬は逆効果。"},
        {"q":"暴力の危険を感じた。適切な行動は？",
         "options":["すぐに助けを呼ぶ","動画を撮る","一人で止める","そのまま放置"],
         "answer_text":"すぐに助けを呼ぶ",
         "explain":"安全最優先。止めに入らず周囲/警察へ。"},
        {"q":"なりすましアカウントが出た。対応は？",
         "options":["公式通報＋相談","無視","反論投稿","本人を探して抗議"],
         "answer_text":"公式通報＋相談",
         "explain":"プラットフォーム通報と相談が最善。"},
        {"q":"食事の場で一人を外している。あなたは？",
         "options":["一緒に座る/声をかける","無視","加害側に乗る","拡散する"],
         "answer_text":"一緒に座る/声をかける",
         "explain":"孤立を防ぐ行動が大切。"},
        {"q":"不適切な画像が送られてきた。正しい対応は？",
         "options":["保存せずブロック＋相談","面白いからシェア","送り返す","やりとりを続ける"],
         "answer_text":"保存せずブロック＋相談",
         "explain":"保存・拡散しない。ブロック＆相談へ。"}
    ]

    # ---- 初回だけシャッフルして固定（再描画で入れ替わらないように）----
    if "quiz_opts" not in st.session_state:
        st.session_state.quiz_opts = []
        rng = random.Random()
        for item in QUESTIONS:
            opts = item["options"][:]
            rng.shuffle(opts)            # ← 正解含めてランダム
            st.session_state.quiz_opts.append(opts)

    # 並び替えボタン（必要なときだけ）
    col_a, col_b = st.columns([1,3])
    with col_a:
        if st.button("並び替える", use_container_width=True):
            # 回答も一旦クリアしてから再シャッフル
            for i in range(len(QUESTIONS)):
                st.session_state.pop(f"q_{i}", None)
            st.session_state.quiz_opts = []
            rng = random.Random()
            for item in QUESTIONS:
                opts = item["options"][:]
                rng.shuffle(opts)
                st.session_state.quiz_opts.append(opts)
            st.rerun()

    # ---- 表示（固定された並びを使用）----
    user_answers = []  # [(choice, correct_text, explain), ...]
    for i, item in enumerate(QUESTIONS):
        st.markdown(f"**Q{i+1}. {item['q']}**")
        opts = st.session_state.quiz_opts[i]
        choice = st.radio(" ", opts, index=None, key=f"q_{i}", label_visibility="collapsed")
        user_answers.append((choice, item["answer_text"], item["explain"]))

    # ---- 採点 ----
    if st.button("採点する", type="primary", use_container_width=True):
        score = 0
        wrongs = []
        for i, (choice, correct, explain) in enumerate(user_answers):
            if choice == correct:
                score += 1
            else:
                wrongs.append((i, correct, choice or "（未回答）", explain))

        st.success(f"スコア：{score} / {len(QUESTIONS)}")
        if score == len(QUESTIONS):
            st.balloons()

        for i, corr, yours, exp in wrongs:
            st.markdown(
                f"""<div class="card alert">
<strong>Q{i+1} 解説：</strong> {exp}<br>
<small>正解：{corr} / あなたの回答：{yours}</small>
</div>""",
                unsafe_allow_html=True
            )

# ================= ページ：相談窓口（地域別） =================
elif page == "相談窓口（地域別）":
    st.markdown("### 相談窓口（地域別）")
    st.caption("※ 迷ったらまず全国共通の番号を。命や安全が心配なら110へ。")

    REGIONS = [
        "北海道・東北",
        "関東",
        "中部",
        "近畿",
        "中国",
        "四国",
        "九州・沖縄",
    ]
    region = st.selectbox("地域を選ぶ", REGIONS, index=2)  # デフォルト=中部

    st.markdown("#### 🧭 すぐに使える全国共通")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("""
<div class="kv"><b>緊急時（命・安全）</b> 110</div>
<div class="kv"><b>警察相談（暴力/脅し等）</b> #9110</div>
<div class="kv"><b>児童相談（虐待通告/子どもの危険）</b> 189（いちはやく）</div>
<div class="kv"><b>24時間子どもSOSダイヤル</b> 0120-0-78310</div>
""", unsafe_allow_html=True)
        st.markdown(
            '<div class="btnlink"><a target="_blank" href="https://www.mhlw.go.jp/mamorouyokokoro/soudan/tel/">厚生労働省 こころの健康相談等（公式ページ）</a></div>',
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### 🔎 公式窓口をすばやく探す（地方ベースの検索リンク）")
    st.caption("※ 正確な最新の連絡先は各公式サイトで確認してください。以下はワンクリック検索リンクです。")

    def google_link(q: str) -> str:
        return "https://www.google.com/search?q=" + urllib.parse.quote(q)

    # 地方名でまとめ検索（都道府県を列挙しない：軽量＆バグ減）
    base_queries = [
        f"{region} 教育委員会 いじめ 相談",
        f"{region} 教育相談センター 電話",
        f"{region} 子ども 家庭 相談 電話",
        f"{region} こころの健康相談 ダイヤル",
        f"{region} 警察 相談 #9110"
    ]
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for q in base_queries:
            st.markdown(f'<div class="kv"><b>検索:</b> <a target="_blank" href="{google_link(q)}">{q}</a></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.info("※ まずは安全を最優先に。危険を感じたら、ためらわず 110 / 189 / #9110 を。")

elif page == "セルフチェック":
    # ================セルフチェック=====================-
    st.markdown(
        """
<div style='background-color:#2563eb; padding:14px; border-radius:10px; color:white; font-weight:800; font-size:20px; letter-spacing:.5px;'>
📒 セルフチェック（ストレス・トラウマ反応・気分）
</div>
""",
        unsafe_allow_html=True
    )
    st.markdown("※ これは医療診断ではありません。結果に関わらず、つらさが続く/強い場合は専門機関へ。")

    # 22問（簡易PTSD/ストレス反応ミックス）
    questions = [
        "最近の出来事が頭から離れず、夢に見ることがある",
        "その出来事を思い出す場面や場所を避けてしまう",
        "似た出来事やニュースを連想すると強い不安を感じる",
        "小さな音や刺激で強く驚いたり過敏に反応する",
        "特定のにおいや音が過去の記憶をよみがえらせる",
        "強い罪悪感や恥の感情が続いている",
        "自分のせいだと繰り返し考えてしまう",
        "イライラや怒りが抑えにくい",
        "無力感や絶望感を感じることが多い",
        "ぼーっとする/現実感がない感覚になることがある",
        "頭痛・腹痛・吐き気・動悸など体の不調が増えた",
        "寝つきが悪い/夜中に目が覚める/悪夢を見る",
        "集中しづらい/物事を忘れやすい",
        "人付き合いやSNSを避けるようになった",
        "以前楽しめたことを楽しめなくなった",
        "学業や仕事のパフォーマンスに影響が出ている",
        "「消えてしまいたい」と感じることがある",
        "加害した人や出来事に強い怒り・復讐心を抱く",
        "他人を信頼しにくくなった",
        "些細な刺激で心拍が上がる・汗ばむなどの反応が出る",
        "急に当時の場面がフラッシュバックすることがある",
        "睡眠や食事など生活リズムが乱れている",
    ]

    # 質問UI（キーは重複しないよう 'sc_q{i}'）
    score = 0
    col_left, col_right = st.columns([2,1])
    with col_left:
        for i, q in enumerate(questions):
            ans = st.radio(q, ["いいえ", "少しある", "よくある"], index=0, key=f"sc_q{i}")
            if ans == "少しある":
                score += 1
            elif ans == "よくある":
                score += 2

    # 結果と保存
    with col_right:
        st.markdown("### 集計 / 結果")
        if st.button("結果を見る", key="sc_result_btn", use_container_width=True):
            # 合計 0〜44 点
            if score <= 10:
                st.success(f"合計 {score} 点：比較的落ち着いている様子。ただし気になる点が続けば専門家に相談を。")
            elif score <= 26:
                st.warning(f"合計 {score} 点：ストレス反応がやや強いかもしれません。信頼できる人や相談窓口に共有を。")
            else:
                st.error(f"合計 {score} 点：強いストレス/トラウマ反応の可能性。専門機関への相談をおすすめします。")

            st.caption("※ 自己チェックです。診断ではありません。強い不安・衝動（自傷・他害など）がある場合は早めに相談先へ。")

            # ダウンロード用のメモ
            memo = "📒 セルフチェック結果\n" + "\n".join(
                [f"- {i+1:02d}. {q} : {st.session_state.get(f'sc_q{i}')}" for i, q in enumerate(questions)]
            ) + f"\n\n合計スコア: {score}\n（0-10:軽度/11-26:中等度/27-:高めの反応）\n"
            st.download_button(
                "📝 この結果をテキストで保存",
                data=memo,
                file_name=f"selfcheck_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )

    # リセット（任意）
    if st.button("🧹 回答をリセット", key="sc_reset", help="全ての選択肢を初期化します"):
        for i in range(len(questions)):
            st.session_state.pop(f"sc_q{i}", None)
        st.rerun()

# ================= フッター =================
st.divider()
st.caption("© こころのまど（学習用MVP）｜個人情報は入力しないでください。")

