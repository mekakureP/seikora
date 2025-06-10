import streamlit as st
import requests
import streamlit.components.v1 as components

MISSKEY_INSTANCE = "seikora.one"
API_TOKEN = st.secrets["MISSKEY_API_TOKEN"]
API_URL = f"https://{MISSKEY_INSTANCE}/api/notes/local-timeline"

st.title("📸 Misskey ローカルTL メディアビューア（seikora.one）")

@st.cache_data(ttl=60)
def fetch_local_timeline(token, limit=30):
    res = requests.post(API_URL, json={"i": token, "limit": limit, "withFiles": True})
    res.raise_for_status()
    return res.json()

try:
    notes = fetch_local_timeline(API_TOKEN)
    media_urls = [
        f["url"]
        for note in notes
        for f in note.get("files", [])
        if f["type"].startswith(("image", "video"))
    ]

    if media_urls:
        # HTMLでスワイプ操作可能なビューワーを埋め込む
        imgs_html = "\n".join(
            f'<img src="{url}" class="media" style="display:none; width:100%; height:auto;">'
            for url in media_urls
        )
        html_code = f"""
        <div id="viewer" style="touch-action: pan-y;">
          {imgs_html}
        </div>
        <script>
          const container = document.getElementById("viewer");
          const imgs = container.querySelectorAll(".media");
          let idx = 0;
          imgs[idx].style.display = "block";
          let startX = 0;

          container.addEventListener("touchstart", e => {{
            startX = e.changedTouches[0].screenX;
          }});

          container.addEventListener("touchend", e => {{
            const diff = e.changedTouches[0].screenX - startX;
            if (Math.abs(diff) > 50) {{
              imgs[idx].style.display = "none";
              idx = (idx + (diff < 0 ? 1 : -1) + imgs.length) % imgs.length;
              imgs[idx].style.display = "block";
            }}
          }});
        </script>
        """
        # 高さはお好みで調整
        components.html(html_code, height=500, scrolling=False)

    else:
        st.info("画像または動画が含まれるノートが見つかりませんでした。")

except Exception as e:
    st.error(f"エラーが発生しました：{e}")


