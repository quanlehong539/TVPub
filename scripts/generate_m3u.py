import json
import urllib.request

TRADATV_API_URL = "https://htdk.httdtvnb.xyz/matches"
GAVANGTV_API_URL = "https://gavangtv-api.adviceme.io/api/v1/matches"
OUTPUT_FILE = "TVPubSports.m3u"


def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
            "Accept": "application/json;charset=utf-8,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_tradatv_entries(raw_data) -> list[str]:
    if isinstance(raw_data, list):
        matches = raw_data
    elif isinstance(raw_data, dict):
        matches = raw_data.get("data") or raw_data.get("matches") or []
    else:
        matches = []

    lines = []
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
                f'#EXTINF:-1 group-title="Trà Đá TV" group-logo="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgyQCSmQcjlaV591HXja0Chg7VvYZfmRWybUV203d2Jcfr-8VQm-DaOZTln2hqUhXQmEH-7CEpe5pc4Gi3H_uPKE8UarQXY38tNnkEZmFuXXjgeEMh7LH1QlMzk69MN9-O-tse-CZxCYTB0Xl1oOeJzt7n0AZmnLWBtmKD87PyWfNZmopLD1pxLUiswHe9N/s600/TraDaTV_logo.png" '
                f'tvg-logo="{avatar_url}", {display_title}'
            )
            lines.append(url)

    return lines


def build_gavangtv_entries(raw_data) -> list[str]:
    if not isinstance(raw_data, dict):
        return []

    data_obj = raw_data.get("data")
    if isinstance(data_obj, dict):
        matches = list(data_obj.values())
    elif isinstance(data_obj, list):
        matches = data_obj
    else:
        matches = []

    lines = []
    for match in matches:
        if not isinstance(match, dict):
            continue

        home_name = ((match.get("homeTeam") or {}).get("name") or "").strip()
        away_name = ((match.get("awayTeam") or {}).get("name") or "").strip()
        if home_name and away_name:
            title = f"{home_name} vs {away_name}"
        else:
            title = (home_name or away_name or "Trận đấu").strip()

        fallback_logo = (
            ((match.get("homeTeam") or {}).get("logo") or "").strip()
            or ((match.get("competition") or {}).get("logo") or "").strip()
        )

        anchors = match.get("anchorAppointmentVoList") or []
        added_any = False

        for anchor in anchors:
            if not isinstance(anchor, dict):
                continue

            nick_name = (anchor.get("nickName") or "").strip()
            avatar_url = (anchor.get("userImage") or "").strip() or fallback_logo
            stream_urls = anchor.get("streamUrls") or []

            # Lấy các luồng hợp lệ (ưu tiên .m3u8 trước, sau đó đến các link khác)
            valid_urls = [u.strip() for u in stream_urls if isinstance(u, str) and u.strip()]
            m3u8_urls = [u for u in valid_urls if ".m3u8" in u.lower()]
            selected_urls = m3u8_urls if m3u8_urls else valid_urls

            label = f"BLV {nick_name}" if nick_name else ""
            display_title = f"{title} [{label}]" if label else title

            for url in selected_urls:
                lines.append(
                    f'#EXTINF:-1 group-title="Gà Vàng 33" group-logo="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgBMx0r-H3ReHAdc_tYvcyeW5wYS_KJcQ_yumoJVfIs5rqMvu18oGGkr55AVSXMdsZMpHS0py9qOS-v8CtOrDYYe19MJYcVG2jffxDWQ2UfPYZtH8wBdieg7WJQtpuWTkgSchYnY_zA5_h65aMD8BRZKVYOILgc0DbMjPpNotW8EkQEwCtmEaAL9FtYF_qv/s600/GaVang33_logo.png" '
                    f'tvg-logo="{avatar_url}", {display_title}'
                )
                lines.append(url)
                added_any = True

        # Fallback sang defaultLink nếu không có stream từ BLV
        if not added_any:
            default_link = (match.get("defaultLink") or "").strip()
            if default_link:
                lines.append(
                    f'#EXTINF:-1 group-title="Gà Vàng 33" '
                    f'tvg-logo="{fallback_logo}", {title}'
                )
                lines.append(default_link)

    return lines


def build_m3u() -> str:
    all_entries = ["#EXTM3U"]

    try:
        tradatv_raw = fetch_json(TRADATV_API_URL)
        all_entries.extend(build_tradatv_entries(tradatv_raw))
    except Exception as exc:
        print(f"Warning: failed to fetch Trà Đá TV: {exc}")

    try:
        gavang_raw = fetch_json(GAVANGTV_API_URL)
        all_entries.extend(build_gavangtv_entries(gavang_raw))
    except Exception as exc:
        print(f"Warning: failed to fetch Gà Vàng 33: {exc}")

    return "\n".join(all_entries) + "\n"


def main() -> None:
    content = build_m3u()

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            old_content = f.read()
    except FileNotFoundError:
        old_content = None

    if content != old_content:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated TVPubSports.m3u")
    else:
        print("No changes in TVPubSports.m3u")


if __name__ == "__main__":
    main()
