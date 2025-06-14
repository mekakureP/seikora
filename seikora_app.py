import streamlit as st
import requests
import json
import streamlit.components.v1 as components
import os

# ────────────────────────────────
# Misskey インスタンス設定
MISSKEY_INSTANCE = "seikora.one"
LOCAL_API_URL    = f"https://{MISSKEY_INSTANCE}/api/notes/local-timeline"
USER_API_URL     = f"https://{MISSKEY_INSTANCE}/api/users/notes"
SHOW_USER_URL    = f"https://{MISSKEY_INSTANCE}/api/users/show"
BATCH_SIZE       = 60
# ────────────────────────────────

st.title("📸 Misskey メディアビューア")

# ── API トークン取得──────────────────
API_TOKEN = os.getenv("MISSKEY_API_TOKEN") or st.secrets.get("MISSKEY_API_TOKEN")
if not API_TOKEN:
    API_TOKEN = st.text_input("Misskey API トークンを入力してください", type="password")
    if not API_TOKEN:
        st.warning("API トークンが設定されていません。入力が必要です。")
        st.stop()

# ── 取得モード選択──────────────────
mode = st.radio("取得モードを選択", ("ローカルTL", "ユーザー指定TL"), index=0)
username = None
if mode == "ユーザー指定TL":
    raw_user = st.text_input("表示するユーザー名を指定（@以下）", value="")
    username = raw_user.lstrip("@") or None

# ── API 呼び出し関数──────────────────
@st.cache_data(ttl=60)
def fetch_batch(token: str, limit: int, until_id: str | None = None):
    payload = {"i": token, "limit": limit, "withFiles": True}
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(LOCAL_API_URL, json=payload)
    res.raise_for_status()
    return res.json()

@st.cache_data(ttl=300)
def fetch_user_id(token: str, username: str) -> str:
    res = requests.post(SHOW_USER_URL, json={"i": token, "username": username})
    res.raise_for_status()
    return res.json().get("id")

@st.cache_data(ttl=60)
def fetch_user_notes(token: str, user_id: str, limit: int, until_id: str | None = None):
    payload = {"i": token, "userId": user_id, "limit": limit,
               "includeMyRenotes": True, "withFiles": True}
    if until_id:
        payload["untilId"] = until_id
    res = requests.post(USER_API_URL, json=payload)
    res.raise_for_status()
    return res.json()

# ── 初回ノート取得──────────────────
if mode == "ユーザー指定TL" and username:
    user_id = fetch_user_id(API_TOKEN, username)
    notes = fetch_user_notes(API_TOKEN, user_id, BATCH_SIZE)
    api_url = USER_API_URL
else:
    notes = fetch_batch(API_TOKEN, BATCH_SIZE)
    api_url = LOCAL_API_URL

# ── メディア＋本文スニペット準備──────────────────
initial_media = []
for note in notes:
    raw_text = note.get("text") or note.get("renote", {}).get("text", "") or ""
    lines = raw_text.split("\n")
    snippet = "\n".join(lines[:3])
    for f in note.get("files", []):
        if f.get("type", "").startswith(("image", "video")):
            initial_media.append({"url": f["url"], "type": f["type"], "text": snippet})
initial_until_id = notes[-1].get("id") if notes else None

# ── HTML/JS ビューア埋め込み──────────────────
html_code = f"""
<style>
  #viewer img, #viewer video {{ width:100%; height:auto; display:block; margin:0 auto; }}
  #snippet-area {{ padding:8px; color:#000; font-size:14px; white-space: pre-wrap; background:#fff; }}
</style>
<div id=\"viewer\"></div>
<div id=\"snippet-area\"></div>
<script>
const apiUrl = \"{api_url}\";
const token  = \"{API_TOKEN}\";
const batchSize = {BATCH_SIZE};
let untilId = {json.dumps(initial_until_id)};
let medias  = {json.dumps(initial_media)};
const viewer      = document.getElementById(\"viewer\");
const snippetArea = document.getElementById(\"snippet-area\");
let idx = 0;

function render() {{
  const item = medias[idx];
  viewer.innerHTML = '';
  let el;
  if (item.type.startsWith(\"video\")) {{
    el = document.createElement(\"video\");
    el.src = item.url;
    el.controls = true;
    el.autoplay = true;
    el.loop = true;
    el.muted = true;
    el.playsInline = true;
    el.setAttribute(\"playsinline\", \"\");
    el.crossOrigin = \"anonymous\";
  }} else {{
    el = document.createElement(\"img\");
    el.src = item.url;
  }}
  viewer.appendChild(el);
  snippetArea.textContent = item.text;
}}

async function loadMore() {{
  const payload = {{ i: token, limit: batchSize }};
  if (untilId) payload.untilId = untilId;
  const res = await fetch(apiUrl, {{ method: \"POST\", headers: {{\"Content-Type\":\"application/json\"}}, body: JSON.stringify(payload) }});
  const notes = await res.json(); if (!notes.length) return;
  untilId = notes[notes.length-1].id;
  notes.forEach(note => {{
    const raw = note.text || note.renote?.text || "";
    const sn = raw.split("\n").slice(0,3).join("\n");
    note.files.forEach(f => {{ if (f.type.startsWith(\"image\")||f.type.startsWith(\"video\")) medias.push({{ url:f.url, type:f.type, text:sn }}); }});
  }});
}}

let startX = 0;
viewer.addEventListener(\"touchstart\", e => {{ startX = e.changedTouches[0].screenX; }});
viewer.addEventListener(\"touchend\", async e => {{
  const diff = e.changedTouches[0].screenX - startX;
  if (Math.abs(diff) > 50) {{ idx = (idx + (diff < 0 ? 1 : -1) + medias.length) % medias.length; if (idx === medias.length - 1) await loadMore(); render(); }}
}});
viewer.addEventListener(\"dblclick\", e => {{
  const x = e.clientX;
  idx = x < window.innerWidth/2 ? (idx-1+medias.length)%medias.length : (idx+1)%medias.length;
  render();
}});

render();
</script>
"""

components.html(
    html_code,
    height=800,
    scrolling=False
)


