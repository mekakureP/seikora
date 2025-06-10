import streamlit as st
import requests

MISSKEY_INSTANCE = "seikora.one"
API_TOKEN = st.secrets["MISSKEY_API_TOKEN"]
API_URL = f"https://{MISSKEY_INSTANCE}/api/notes/local-timeline"

st.title("📸 Misskey ローカルTL メディアビューア（seikora.one）")

@st.cache_data(ttl=60)
def fetch_local_timeline(token, limit=30):
    headers = {"Content-Type": "application/json"}
    payload = {"i": token, "limit": limit, "withFiles": True}
    res = requests.post(API_URL, json=payload, headers=headers)
    res.raise_for_status()
    return res.json()

try:
    notes = fetch_local_timeline(API_TOKEN)
    media_urls = []
    for note in notes:
        for f in note.get("files", []):
            if f["type"].startswith(("image", "video")):
                media_urls.append(f["url"])

    if media_urls:
        idx = st.slider("メディア選択", 0, len(media_urls)-1, 0)
        current_url = media_urls[idx]

        if current_url.endswith((".mp4", ".webm")):
            st.video(current_url)
        else:
            st.image(current_url, use_container_width=True)
    else:
        st.info("画像または動画が含まれるノートが見つかりませんでした。")

except Exception as e:
    st.error(f"エラーが発生しました：{e}")

