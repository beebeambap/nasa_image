#!/usr/bin/env python3
"""NASA APOD → ntfy 전송 스크립트.

매일 NASA Astronomy Picture of the Day(APOD)를 조회하여,
이미지인 경우 ntfy.sh 토픽으로 푸시 알림(이미지 첨부 포함)을 전송한다.

표준 라이브러리만 사용하므로 추가 의존성이 없다.

필요한 환경 변수:
    NASA_API_KEY   NASA API 키 (없으면 DEMO_KEY 사용 — 호출 제한 있음)
    NTFY_TOPIC     ntfy.sh 토픽명 (필수)
    NTFY_SERVER    ntfy 서버 (선택, 기본값 https://ntfy.sh)
    APOD_DATE      조회할 날짜 YYYY-MM-DD (선택, 기본값 오늘)

종료 코드:
    0  정상 전송 완료
    1  설정 오류 (예: NTFY_TOPIC 미설정)
    2  영상(video) 타입이라 배경화면 스킵 (실패 아님)
    3  NASA API 또는 ntfy 전송 실패
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

NASA_APOD_ENDPOINT = "https://api.nasa.gov/planetary/apod"
DEFAULT_NTFY_SERVER = "https://ntfy.sh"
MAX_RETRIES = 4
RETRY_BACKOFF_BASE = 2  # 초 단위: 2, 4, 8, 16


def log(msg: str) -> None:
    """타임스탬프 없이 stderr로 로그 출력 (Actions 로그 가독성용)."""
    print(msg, file=sys.stderr, flush=True)


# 일시적 오류로 보고 재시도할 HTTP 상태 코드 (그 외 4xx는 즉시 실패)
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def http_get_json(url: str) -> dict:
    """GET 요청 후 JSON 파싱.

    네트워크 오류·타임아웃·일시적 5xx/429는 지수 백오프로 재시도하고,
    그 외 4xx(403/401/400 등)는 응답 본문을 출력하고 즉시 실패한다.
    """
    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nasa-apod-wallpaper/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
            return json.loads(body)
        except urllib.error.HTTPError as err:
            # NASA(api.data.gov)는 오류 원인을 본문 JSON에 담아 보낸다 → 그대로 노출
            detail = ""
            try:
                detail = err.read().decode("utf-8", "replace").strip()
            except Exception:  # noqa: BLE001 - 본문 읽기 실패는 무시
                pass
            log(f"[경고] NASA API HTTP {err.code} 응답: {detail or '(본문 없음)'}")
            if err.code not in RETRYABLE_STATUS:
                # 키 오류 등은 재시도해도 동일하므로 즉시 중단
                raise RuntimeError(
                    f"NASA API가 HTTP {err.code}를 반환했습니다 (재시도 불가). 응답: {detail or '(본문 없음)'}"
                ) from err
            last_err = err
        except (urllib.error.URLError, TimeoutError, ValueError) as err:
            last_err = err
            log(f"[경고] NASA API 호출 실패 (시도 {attempt}/{MAX_RETRIES}): {err}")

        wait = RETRY_BACKOFF_BASE ** attempt
        if attempt < MAX_RETRIES:
            log(f"       {wait}초 후 재시도...")
            time.sleep(wait)
    raise RuntimeError(f"NASA API 호출이 {MAX_RETRIES}회 모두 실패했습니다: {last_err}")


def fetch_apod(api_key: str, date: str | None) -> dict:
    """APOD 데이터를 조회한다."""
    url = f"{NASA_APOD_ENDPOINT}?api_key={api_key}"
    if date:
        url += f"&date={date}"
    return http_get_json(url)


def pick_image_url(apod: dict) -> str:
    """배경화면용 이미지 URL 선택. hdurl 우선, 없으면 url로 폴백."""
    return apod.get("hdurl") or apod["url"]


def send_to_ntfy(server: str, topic: str, title: str, message: str, attach_url: str) -> None:
    """ntfy 토픽으로 이미지 첨부 알림 전송. 실패 시 지수 백오프로 재시도."""
    url = f"{server.rstrip('/')}/{topic}"
    headers = {
        "Title": title,
        "Tags": "milky_way",
        "Attach": attach_url,
        "Content-Type": "text/plain; charset=utf-8",
    }
    data = message.encode("utf-8")

    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                if 200 <= resp.status < 300:
                    return
                raise RuntimeError(f"ntfy 응답 상태 코드 {resp.status}")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError) as err:
            last_err = err
            wait = RETRY_BACKOFF_BASE ** attempt
            log(f"[경고] ntfy 전송 실패 (시도 {attempt}/{MAX_RETRIES}): {err}")
            if attempt < MAX_RETRIES:
                log(f"       {wait}초 후 재시도...")
                time.sleep(wait)
    raise RuntimeError(f"ntfy 전송이 {MAX_RETRIES}회 모두 실패했습니다: {last_err}")


def main() -> int:
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        log("[오류] NTFY_TOPIC 환경 변수가 설정되지 않았습니다.")
        return 1

    api_key = os.environ.get("NASA_API_KEY", "").strip() or "DEMO_KEY"
    if api_key == "DEMO_KEY":
        log("[경고] NASA_API_KEY가 없어 DEMO_KEY를 사용합니다 (호출 제한 있음).")
    server = os.environ.get("NTFY_SERVER", DEFAULT_NTFY_SERVER).strip()
    date = os.environ.get("APOD_DATE", "").strip() or None

    try:
        apod = fetch_apod(api_key, date)
    except RuntimeError as err:
        log(f"[오류] {err}")
        return 3

    media_type = apod.get("media_type", "unknown")
    title = apod.get("title", "NASA APOD")
    apod_date = apod.get("date", "")
    log(f"[정보] APOD 조회 완료: date={apod_date}, title={title!r}, media_type={media_type}")

    if media_type != "image":
        log(f"[정보] 이미지가 아닌 '{media_type}' 타입이라 배경화면 전송을 건너뜁니다.")
        return 2

    image_url = pick_image_url(apod)
    notify_title = f"🚀 NASA 오늘의 우주 사진: {title}"
    body = f"{title}\n{apod_date}"

    try:
        send_to_ntfy(server, topic, notify_title, body, image_url)
    except RuntimeError as err:
        log(f"[오류] {err}")
        return 3

    log(f"[성공] ntfy 전송 완료 → {server.rstrip('/')}/{topic}")
    log(f"        이미지 URL: {image_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
