# 🚀 NASA APOD 자동 배경화면

NASA의 **Astronomy Picture of the Day(APOD)** 를 매일 자동으로 받아와 Android 기기의 배경화면으로 설정하는 무료 자동화 파이프라인입니다.

> IFTTT 유료화를 대체하기 위한 자체 구현 프로젝트입니다. 전체 설계 배경과 인수인계 내용은 [`docs/handover.md`](docs/handover.md)를 참고하세요.

## 아키텍처

```
GitHub Actions (cron, 매일 KST 09:00)
        │  NASA APOD API 호출
        ▼
   scripts/nasa_apod.py
        │  media_type=image 인 경우만
        ▼
     ntfy.sh (푸시 알림 + 이미지 첨부)
        │
        ▼
  Android: ntfy 앱 → MacroDroid → 배경화면 자동 설정
```

이 저장소가 담당하는 부분은 **클라우드 측(GitHub Actions + NASA API + ntfy 전송)** 입니다.
Android 측(ntfy 앱 + MacroDroid)은 기기에서 직접 설정하며, 아래 [Android 설정](#android-설정)을 따르세요.

## 저장소 구성

| 경로 | 설명 |
|------|------|
| `.github/workflows/nasa_wallpaper.yml` | 매일 실행되는 GitHub Actions 워크플로 |
| `scripts/nasa_apod.py` | NASA APOD 조회 → ntfy 전송 (표준 라이브러리만 사용, 의존성 0) |
| `docs/handover.md` | 프로젝트 인수인계 설계서 |

## 빠른 시작

### 1. NASA API 키 발급
[api.nasa.gov](https://api.nasa.gov) 에서 무료로 발급받습니다 (1,000 requests/hour).

### 2. ntfy 토픽 결정
추측하기 어려운 고유 토픽명을 정합니다. 예: `my-nasa-wall-a7f3k9` (UUID 형식 권장).
ntfy 토픽은 사실상 비밀번호 역할을 하므로 공개하지 마세요.

### 3. GitHub Secrets 등록
저장소 **Settings → Secrets and variables → Actions** 에서 등록합니다.

| Secret | 값 |
|--------|-----|
| `NASA_API_KEY` | NASA에서 발급받은 키 |
| `NTFY_TOPIC` | 위에서 정한 고유 토픽명 |

### 4. 수동 테스트
**Actions → NASA APOD Wallpaper Update → Run workflow** 로 즉시 실행해 봅니다.
`date` 입력란에 특정 날짜(`YYYY-MM-DD`)를 넣어 과거 APOD를 테스트할 수도 있습니다.

### 5. Android 설정
아래 [Android 설정](#android-설정) 절차를 따릅니다.

## 스크립트 동작 / 종료 코드

`scripts/nasa_apod.py` 는 다음 환경 변수를 사용합니다.

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `NTFY_TOPIC` | ✅ | — | ntfy 토픽명 |
| `NASA_API_KEY` | ❌ | `DEMO_KEY` | NASA API 키 (DEMO_KEY는 호출 제한 큼) |
| `NTFY_SERVER` | ❌ | `https://ntfy.sh` | 자체 호스팅 ntfy 서버 사용 시 |
| `APOD_DATE` | ❌ | 오늘 | 조회할 날짜 `YYYY-MM-DD` |

| 종료 코드 | 의미 |
|-----------|------|
| `0` | 정상 전송 완료 |
| `1` | 설정 오류 (예: `NTFY_TOPIC` 미설정) |
| `2` | 영상(video) 타입이라 배경화면 스킵 — 워크플로에서는 성공 처리 |
| `3` | NASA API 또는 ntfy 전송 실패 (각 4회 지수 백오프 재시도 후) |

### 로컬 실행 예시
```bash
export NASA_API_KEY="여기에_키"
export NTFY_TOPIC="my-nasa-wall-a7f3k9"
python3 scripts/nasa_apod.py
```

## Android 설정

### ntfy 앱
1. Play Store에서 **ntfy** 설치
2. 위에서 정한 토픽명을 **구독(Subscribe)**
3. 워크플로를 수동 실행해 알림(이미지 첨부)이 도착하는지 확인

### MacroDroid 매크로
1. Play Store에서 **MacroDroid** 설치 (무료: 매크로 5개 한도)
2. 매크로 생성:
   - **트리거**: 앱 알림 수신 → 앱 `ntfy`, 조건: 알림에 `NASA` 포함
   - **액션**:
     1. 알림 첨부(Attachment) URL에서 이미지 다운로드 → 임시 저장
     2. 배경화면 설정 (홈 화면 / 잠금화면 선택)
     3. (선택) 임시 파일 삭제
3. MacroDroid를 **배터리 최적화 예외**에 등록 (필수 — 안 하면 백그라운드 알림이 누락됨)
4. 전체 파이프라인 end-to-end 테스트

## 엣지케이스 처리

| 상황 | 처리 |
|------|------|
| APOD가 영상(YouTube)인 날 | `media_type` 체크 후 전송 스킵 (종료 코드 2) |
| NASA API 호출 실패 | 4회 지수 백오프(2·4·8·16초) 재시도 |
| ntfy 전송 실패 | 4회 지수 백오프 재시도 |
| `hdurl` 없음 | 일반 해상도 `url` 로 자동 폴백 |
| Android 절전 모드 | MacroDroid 배터리 최적화 예외 등록 필수 |

## 비용

| 서비스 | 비용 | 한도 |
|--------|------|------|
| NASA APOD API | 무료 | 1,000 req/hour |
| GitHub Actions | 무료 | Public repo 무제한 |
| ntfy.sh | 무료 | 250 messages/day |
| MacroDroid | 무료 | 매크로 5개 |
| **합계** | **$0** | |

## 참고

- NASA API: https://api.nasa.gov · [APOD 문서](https://github.com/nasa/apod-api)
- ntfy: https://docs.ntfy.sh
- MacroDroid: https://www.macrodroid.com
- cron 문법: https://crontab.guru
