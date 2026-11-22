import json
import urllib.request

API_URL = "https://htdk.httdtvnb.xyz/matches"
OUTPUT_FILE = "TraDaTV.m3u"


def fetch_matches(url: str) -> list:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
            "Accept": "text/html,application/json;charset=utf-8,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, list):
            return data
        return data.get("data") or data.get("matches") or []


def build_m3u(matches: list) -> str:
    lines = ["#EXTM3U group-logo="https://raw.githubusercontent.com/quanlehong539/TVPub/refs/heads/main/TraDaTV_logo.png""]

    for match in matches:
        title = (match.get("title") or "Trận đấu").strip()
        sport = (match.get("sport") or "").strip()
        commentators = match.get("commentators") or []
        streams = match.get("streams") or []

        blv_map = {c.get("id"): c for c in commentators if c.get("id")}
        default_blv = commentators[0] if commentators else {}

        for stream in streams:
            url = (stream.get("url") or "").strip()
            if not url:
                continue

            blv = blv_map.get(stream.get("commentatorId")) or default_blv
            avatar_url = (blv.get("avatarUrl") or "").strip()

            label = (stream.get("label") or "").strip()
            if not label and blv.get("name"):
                label = f"BLV {blv['name'].strip()}"

            display_title = f"{title} [{label}]" if label else title
            sport_attr = f' tvg-sport="{sport}"' if sport else ""

            lines.append(
                f'#EXTINF:-1 group-title="Trà Đá TV" '
                f'tvg-logo="{avatar_url}"{sport_attr}, {display_title}'
            )
            lines.append(url)

    return "\n".join(lines) + "\n"


def main() -> None:
    matches = fetch_matches(API_URL)
    content = build_m3u(matches)

    # Tránh commit lại nếu nội dung không thay đổi
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            old_content = f.read()
    except FileNotFoundError:
        old_content = None

    if content != old_content:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated playlist.m3u")
    else:
        print("No changes in playlist.m3u")


if __name__ == "__main__":
    main()
