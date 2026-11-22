import json
import urllib.request

TRADATV_API_URL = "https://htdk.httdtvnb.xyz/matches"
GAVANGTV_API_URL = "https://gavangtv-api.adviceme.io/api/v1/matches"
OUTPUT_FILE = "TVPubSports.m3u"
# Đặt True để chỉ lấy trận đang live; False để lấy tất cả
ONLY_LIVE = False
# Đặt True để lấy cả .m3u8 và .flv cho Gà Vàng TV; False để chỉ ưu tiên .m3u8
INCLUDE_FLV_GAVANG = True

def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*; charset=UTF-8",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def format_iso_to_vn(iso_str: str) -> str:
    if not iso_str or not isinstance(iso_str, str):
        return ""
    try:
        normalized = iso_str.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized).astimezone(VN_TZ)
        return dt.strftime("%H:%M %d/%m")
    except ValueError:
        return ""

def format_timestamp_to_vn(ts) -> str:
    if ts is None:
        return ""
    try:
        dt = datetime.fromtimestamp(float(ts), tz=VN_TZ)
        return dt.strftime("%H:%M %d/%m")
    except (ValueError, TypeError, OSError):
        return ""

def is_tradatv_live(match: dict) -> bool:
    status = str(match.get("status") or "").strip().lower()
    return status in {"live", "playing", "in_progress"}

def is_gavangtv_live(match: dict) -> bool:
    m_type = str(match.get("matchType") or "").strip().lower()
    m_status = str(match.get("matchStatus") or "").strip().lower()
    return "live" in {m_type, m_status}

def format_channel_name(time_str: str, title: str, blv_label: str, fmt_tag: str = "") -> str:
    time_part = f"[{time_str.strip()}] " if time_str and time_str.strip() else ""
    blv_part = f" [{blv_label.strip()}]" if blv_label and blv_label.strip() else ""
    fmt_part = f" [{fmt_tag.strip()}]" if fmt_tag and fmt_tag.strip() else ""
    return f"{time_part}{title.strip()}{blv_part}{fmt_part}"

def detect_stream_format(url: str) -> str:
    lower = url.lower()
    if ".m3u8" in lower:
        return "M3U8"
    if ".flv" in lower:
        return "FLV"
    return ""

def build_tradatv_entries(raw_data) -> list[str]:
    if isinstance(raw_data, list):
        matches = raw_data
    elif isinstance(raw_data, dict):
        matches = raw_data.get("data") or raw_data.get("matches") or []
    else:
        matches = []

    lines = []
    for match in matches:
        if not isinstance(match, dict):
            continue
        if ONLY_LIVE and not is_tradatv_live(match):
            continue
            
        title = (match.get("title") or "Trận đấu").strip()
        sport = (match.get("sport") or "").strip()
        time_str = format_iso_to_vn(match.get("startTime") or "")
        commentators = match.get("commentators") or []
        streams = match.get("streams") or []

        blv_map = {c.get("id"): c for c in commentators if isinstance(c, dict) and c.get("id")}
        default_blv = commentators[0] if commentators and isinstance(commentators[0], dict) else {}

        for stream in streams:
            if not isinstance(stream, dict):
                continue

            url = (stream.get("url") or "").strip()
            if not url:
                continue

            blv = blv_map.get(stream.get("commentatorId")) or default_blv
            avatar_url = (blv.get("avatarUrl") or "").strip()

            raw_label = (stream.get("label") or "").strip()
            if not raw_label and blv.get("name"):
                raw_label = f"BLV {blv['name'].strip()}"

            display_title = format_channel_name(time_str, title, raw_label)

            lines.append(
                f'#EXTINF:-1 group-title="🔴 ⚽ 🏐 TRÀ ĐÁ TV" group-logo="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgyQCSmQcjlaV591HXja0Chg7VvYZfmRWybUV203d2Jcfr-8VQm-DaOZTln2hqUhXQmEH-7CEpe5pc4Gi3H_uPKE8UarQXY38tNnkEZmFuXXjgeEMh7LH1QlMzk69MN9-O-tse-CZxCYTB0Xl1oOeJzt7n0AZmnLWBtmKD87PyWfNZmopLD1pxLUiswHe9N/s260/TraDaTV_logo.png" '
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
        if ONLY_LIVE and not is_gavangtv_live(match):
            continue
            
        home_name = ((match.get("homeTeam") or {}).get("name") or "").strip()
        away_name = ((match.get("awayTeam") or {}).get("name") or "").strip()
        if home_name and away_name:
            title = f"{home_name} vs {away_name}"
        else:
            title = (home_name or away_name or "Trận đấu").strip()

        norm_time = (match.get("matchNormalizedTime") or "").strip()
        norm_date = (match.get("matchNormalizedDate") or "").strip()
        ts_time = format_timestamp_to_vn(match.get("matchTime"))
        time_str = norm_time or norm_date or ts_time

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

            valid_urls = [u.strip() for u in stream_urls if isinstance(u, str) and u.strip()]
            m3u8_urls = [u for u in valid_urls if ".m3u8" in u.lower()]
            if INCLUDE_FLV_GAVANG:
                selected_urls = valid_urls
            else:
                selected_urls = m3u8_urls if m3u8_urls else valid_urls
            
            label = f"BLV {nick_name}" if nick_name else ""
            display_title = format_channel_name(time_str, title, blv_label)
            
            for url in selected_urls:
                lines.append(
                    f'#EXTINF:-1 group-title="🔴 ⚽ GÀ VÀNG 33" group-logo="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgBMx0r-H3ReHAdc_tYvcyeW5wYS_KJcQ_yumoJVfIs5rqMvu18oGGkr55AVSXMdsZMpHS0py9qOS-v8CtOrDYYe19MJYcVG2jffxDWQ2UfPYZtH8wBdieg7WJQtpuWTkgSchYnY_zA5_h65aMD8BRZKVYOILgc0DbMjPpNotW8EkQEwCtmEaAL9FtYF_qv/s197/GaVang33_logo.png" '
                    f'tvg-logo="{avatar_url}", {display_title}'
                )
                lines.append(url)
                added_any = True

        # Fallback sang defaultLink nếu không có stream từ BLV
        if not added_any:
            default_link = (match.get("defaultLink") or "").strip()
            if default_link:
                lines.append(
                    f'#EXTINF:-1 group-title="🔴 ⚽ GÀ VÀNG 33" group-logo="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgBMx0r-H3ReHAdc_tYvcyeW5wYS_KJcQ_yumoJVfIs5rqMvu18oGGkr55AVSXMdsZMpHS0py9qOS-v8CtOrDYYe19MJYcVG2jffxDWQ2UfPYZtH8wBdieg7WJQtpuWTkgSchYnY_zA5_h65aMD8BRZKVYOILgc0DbMjPpNotW8EkQEwCtmEaAL9FtYF_qv/s197/GaVang33_logo.png" '
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
