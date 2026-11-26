import json
import urllib.request

TRADATV_API_URL = "https://htdk.httdtvnb.xyz/matches"
GAVANGTV_API_URL = "https://gavangtv-api.adviceme.io/api/v1/matches"
COLATV_API_URL = "https://api.gvapi.cc/api/matches"

OUTPUT_FILE = "TVPubSports.m3u"


TRADATV_LOGO = "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgyQCSmQcjlaV591HXja0Chg7VvYZfmRWybUV203d2Jcfr-8VQm-DaOZTln2hqUhXQmEH-7CEpe5pc4Gi3H_uPKE8UarQXY38tNnkEZmFuXXjgeEMh7LH1QlMzk69MN9-O-tse-CZxCYTB0Xl1oOeJzt7n0AZmnLWBtmKD87PyWfNZmopLD1pxLUiswHe9N/s600/TraDaTV_logo.png"

GAVANGTV_LOGO = "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgBMx0r-H3ReHAdc_tYvcyeW5wYS_KJcQ_yumoJVfIs5rqMvu18oGGkr55AVSXMdsZMpHS0py9qOS-v8CtOrDYYe19MJYcVG2jffxDWQ2UfPYZtH8wBdieg7WJQtpuWTkgSchYnY_zA5_h65aMD8BRZKVYOILgc0DbMjPpNotW8EkQEwCtmEaAL9FtYF_qv/s197/GaVang33_logo.png"

COLATV_LOGO = "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiszG-AHjhrtvTaL1YsAR7TlCt__G3e61v5F5xS-eSAp2rSKOgWIgb4Ya-FrrGEkuTC-8qntEqBWRDK5jdN-yTuXol0VhsAx7Y534NSzvDFNnGIvNq2S_lDgXKylN9Fl8QTT2L14sY5U5eszhebkLshRph9eYfv1_6eQpTHTfQ2oCOfbdVlsRP3FTC_hETe/s234/ColaTV_logo.png"

def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/154.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json;charset=utf-8,*/*",
        },
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
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

        blv_map = {
            c.get("id"): c
            for c in commentators
            if c.get("id")
        }

        default_blv = commentators[0] if commentators else {}

        for stream in streams:
            url = (stream.get("url") or "").strip()

            if not url:
                continue

            blv = (
                blv_map.get(stream.get("commentatorId"))
                or default_blv
            )

            avatar_url = (blv.get("avatarUrl") or "").strip()

            label = (stream.get("label") or "").strip()

            if not label and blv.get("name"):
                label = f"BLV {blv['name'].strip()}"

            display_title = (
                f"{title} [{label}]" if label else title
            )

            sport_attr = (
                f' tvg-sport="{sport}"' if sport else ""
            )

            lines.append(
                f'#EXTINF:-1 group-title="🔴 ⚽ 🏐 TRÀ ĐÁ TV" '
                f'group-logo="{TRADATV_LOGO}"'
                f'{sport_attr} '
                f'tvg-logo="{avatar_url}", {display_title}'
            )

            lines.append(url)

    return lines

# ==========================================================
# COLA TV
# ==========================================================

def build_colatv_entries(raw_data) -> list[str]:
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

        # Lấy tên hai đội
        home_name = (
            match.get("homeTeamName")
            or (match.get("home_team") or {}).get("name")
            or ""
        ).strip()

        away_name = (
            match.get("awayTeamName")
            or (match.get("away_team") or {}).get("name")
            or ""
        ).strip()

        if home_name and away_name:
            title = f"{home_name} vs {away_name}"
        else:
            title = home_name or away_name or "Trận đấu"

        # Logo đội chủ nhà hoặc logo giải đấu
        fallback_logo = (
            match.get("homeTeamLogo")
            or (match.get("home_team") or {}).get("logo")
            or (match.get("competition") or {}).get("logo")
            or ""
        ).strip()

        anchors = match.get("anchorAppointmentVoList") or []

        for anchor in anchors:
            if not isinstance(anchor, dict):
                continue

            nick_name = (anchor.get("nickName") or "").strip()

            avatar_url = (
                (anchor.get("userImage") or "").strip()
                or fallback_logo
            )

            # Thu thập toàn bộ link livestream
            raw_urls = []

            # 1. Ưu tiên các server m3u8
            servers = anchor.get("servers") or []

            if isinstance(servers, list):
                raw_urls.extend(
                    u for u in servers
                    if isinstance(u, str)
                )

            # 2. Link m3u8 chính
            play_address2 = anchor.get("playStreamAddress2")

            if isinstance(play_address2, str):
                raw_urls.append(play_address2)

            # 3. Link FLV dự phòng
            play_address = anchor.get("playStreamAddress")

            if isinstance(play_address, str):
                raw_urls.append(play_address)

            # Làm sạch và loại bỏ link trùng
            valid_urls = list(dict.fromkeys(
                u.strip()
                for u in raw_urls
                if u.strip()
            ))

            # Ưu tiên m3u8, nếu không có thì lấy link khác
            m3u8_urls = [
                u for u in valid_urls
                if ".m3u8" in u.lower()
            ]

            selected_urls = m3u8_urls or valid_urls

            if not selected_urls:
                continue

            # Tránh lặp tiền tố BLV
            if nick_name:
                if nick_name.upper().startswith("BLV "):
                    label = nick_name
                else:
                    label = f"BLV {nick_name}"
            else:
                label = ""

            display_title = (
                f"{title} [{label}]" if label else title
            )

            for url in selected_urls:
                lines.append(
                    f'#EXTINF:-1 group-title="🔴 ⚽ 🏀 COLA TV" '
                    f'group-logo="{COLATV_LOGO}" '
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

        home = match.get("homeTeam") or {}
        away = match.get("awayTeam") or {}

        home_name = (home.get("name") or "").strip()
        away_name = (away.get("name") or "").strip()

        if home_name and away_name:
            title = f"{home_name} vs {away_name}"
        else:
            title = home_name or away_name or "Trận đấu"

        fallback_logo = (
            (home.get("logo") or "").strip()
            or (
                (match.get("competition") or {}).get("logo")
                or ""
            ).strip()
        )

        anchors = match.get("anchorAppointmentVoList") or []
        added_any = False

        for anchor in anchors:
            if not isinstance(anchor, dict):
                continue

            nick_name = (anchor.get("nickName") or "").strip()
            avatar_url = (
                (anchor.get("userImage") or "").strip()
                or fallback_logo
            )

            stream_urls = anchor.get("streamUrls") or []

            valid_urls = list(dict.fromkeys(
                u.strip()
                for u in stream_urls
                if isinstance(u, str) and u.strip()
            ))

            m3u8_urls = [
                u for u in valid_urls
                if ".m3u8" in u.lower()
            ]

            selected_urls = m3u8_urls or valid_urls

            label = f"BLV {nick_name}" if nick_name else ""
            display_title = (
                f"{title} [{label}]" if label else title
            )

            for url in selected_urls:
                lines.append(
                    f'#EXTINF:-1 group-title="🔴 ⚽ GÀ VÀNG 33" '
                    f'group-logo="{GAVANGTV_LOGO}" '
                    f'tvg-logo="{avatar_url}", {display_title}'
                )

                lines.append(url)
                added_any = True

        # Fallback sang defaultLink nếu không có stream từ BLV
        if not added_any:
            default_link = (match.get("defaultLink") or "").strip()

            if default_link:
                lines.append(
                    f'#EXTINF:-1 group-title="🔴 ⚽ GÀ VÀNG 33" '
                    f'group-logo="{GAVANGTV_LOGO}" '
                    f'tvg-logo="{fallback_logo}", {title}'
                )

                lines.append(default_link)

    return lines

# ==========================================================
# BUILD PLAYLIST
# ==========================================================

def build_m3u() -> str:
    all_entries = ["#EXTM3U"]

    sources = [
        (
            "Trà Đá TV",
            TRADATV_API_URL,
            build_tradatv_entries,
        ),
        (
            "Cola TV",
            COLATV_API_URL,
            build_colatv_entries,
        ),
        (
            "Gà Vàng 33",
            GAVANGTV_API_URL,
            build_gavangtv_entries,
        )
    ]

    for source_name, api_url, builder in sources:
        try:
            raw_data = fetch_json(api_url)
            entries = builder(raw_data)

            all_entries.extend(entries)

            print(
                f"{source_name}: "
                f"{len(entries) // 2} luồng được thêm"
            )

        except Exception as exc:
            print(
                f"Warning: failed to fetch "
                f"{source_name}: {exc}"
            )

    return "\n".join(all_entries) + "\n"


# ==========================================================
# MAIN
# ==========================================================

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

        print(f"Updated {OUTPUT_FILE}")
    else:
        print(f"No changes in {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
