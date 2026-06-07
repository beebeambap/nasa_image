# 🚀 NASA APOD Android 자동 배경화면 프로젝트 — 인수인계 설계서 v1.0

작성일: 2026-06-07

> 본 문서는 프로젝트 초기 설계 자료입니다. 구현된 코드는 저장소 루트의 [`README.md`](../README.md)를 함께 참고하세요.

---

## 1. 프로젝트 개요

### 목적
NASA의 **Astronomy Picture of the Day (APOD)** API를 활용하여, 매일 새로운 우주 사진을 Android 기기의 배경화면으로 자동 업데이트하는 자동화 파이프라인 구축.

### 기존 레퍼런스
- **IFTTT** 레시피 기반 아이디어 (NASA Image of the Day → Android wallpaper update)
- IFTTT의 유료화로 인해 자체 구현으로 전환

### 핵심 가치
| 항목 | 내용 |
|------|------|
| 비용 | 거의 무료 (GitHub Actions 무료 티어 + MacroDroid 무료) |
| 자동화 | 매일 자동 실행, 수동 개입 불필요 |
| 커스터마이징 | IFTTT 대비 자유로운 확장 가능 |

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   CLOUD (GitHub Actions)                 │
│  ┌─────────────┐     ┌──────────────┐     ┌──────────┐  │
│  │  cron 스케줄 │────▶│  NASA APOD   │────▶│  ntfy.sh │  │
│  │  (매일 09시) │     │  API 호출    │     │  푸시 알림│  │
│  └─────────────┘     └──────────────┘     └──────────┘  │
└─────────────────────────────────────────────────────────┘
                                                  │
                                                  ▼ (이미지 URL 포함 알림)
┌─────────────────────────────────────────────────────────┐
│                  ANDROID (사용자 기기)                   │
│  ┌───────────┐     ┌──────────────┐     ┌────────────┐  │
│  │  ntfy 앱  │────▶│  MacroDroid  │────▶│  배경화면  │  │
│  │  알림 수신 │     │  트리거 감지  │     │  자동 설정 │  │
│  └───────────┘     └──────────────┘     └────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 구성 요소 상세

### 3-1. NASA APOD API
| 항목 | 내용 |
|------|------|
| 엔드포인트 | `https://api.nasa.gov/planetary/apod` |
| 인증 | API Key (무료 발급, api.nasa.gov) |
| 무료 제한 | 1,000 requests/hour |
| 주요 응답 필드 | `url`, `hdurl`, `title`, `explanation`, `date`, `media_type` |
| 주의사항 | 당일 사진이 영상(YouTube)이면 `media_type != "image"` → 타입 체크 필요 |

### 3-2. GitHub Actions
역할: 매일 정해진 시간에 NASA API를 호출하고 이미지 URL을 ntfy로 전송.
구현: [`.github/workflows/nasa_wallpaper.yml`](../.github/workflows/nasa_wallpaper.yml) → [`scripts/nasa_apod.py`](../scripts/nasa_apod.py) 실행.

필요한 GitHub Secrets:
| Secret | 값 |
|--------|-----|
| `NASA_API_KEY` | NASA API 키 |
| `NTFY_TOPIC` | 본인만 아는 고유 토픽명 |

### 3-3. ntfy.sh
GitHub Actions → Android 기기로 이미지 URL을 전달하는 무료 푸시 브릿지. 토픽명을 추측하기 어렵게 설정(UUID 권장).

### 3-4. MacroDroid
ntfy 알림 감지 → 이미지 URL 추출 → 배경화면 설정. 무료 한도 매크로 5개. 배터리 최적화 예외 등록 필수.

---

## 4. 구현 단계별 체크리스트

### Phase 1: 준비
- [ ] NASA API Key 발급
- [ ] GitHub Repository 생성
- [ ] ntfy 토픽명 결정
- [ ] Android에 `ntfy` 앱 설치 및 토픽 구독
- [ ] Android에 `MacroDroid` 설치

### Phase 2: GitHub 설정
- [x] `.github/workflows/nasa_wallpaper.yml` 생성
- [x] `scripts/nasa_apod.py` 작성
- [ ] Secrets에 `NASA_API_KEY` 등록
- [ ] Secrets에 `NTFY_TOPIC` 등록
- [ ] `workflow_dispatch` 수동 테스트
- [ ] Actions 로그 성공 확인

### Phase 3: Android 설정
- [ ] ntfy 알림 수신 확인
- [ ] MacroDroid 매크로 생성 (트리거 / 다운로드 / 배경화면)
- [ ] 배터리 최적화 예외 설정
- [ ] end-to-end 테스트

### Phase 4: 검증
- [ ] 다음날 자동 실행 확인
- [ ] 영상 타입 날의 예외 처리 확인

---

## 5. 예외 처리 및 엣지케이스

| 상황 | 처리 방법 |
|------|-----------|
| APOD가 영상인 날 | `media_type` 체크 후 스킵 (종료 코드 2) |
| API 호출 실패 | 4회 지수 백오프 재시도 |
| ntfy 전송 실패 | 4회 지수 백오프 재시도 |
| `hdurl` 없음 | `url`로 폴백 |
| Android 절전 모드 | MacroDroid 배터리 최적화 예외 등록 |

---

## 6. 비용 요약

| 서비스 | 비용 | 한도 |
|--------|------|------|
| NASA APOD API | 무료 | 1,000 req/hour |
| GitHub Actions | 무료 | Public repo 무제한 |
| ntfy.sh | 무료 | 250 messages/day |
| MacroDroid | 무료 | 매크로 5개 |
| **합계** | **$0** | |

---

## 7. 참고 링크

| 항목 | URL |
|------|-----|
| NASA API 발급 | https://api.nasa.gov |
| NASA APOD 문서 | https://github.com/nasa/apod-api |
| ntfy 공식 문서 | https://docs.ntfy.sh |
| MacroDroid 공식 | https://www.macrodroid.com |
| GitHub Actions cron | https://crontab.guru |

---

## 8. 향후 확장 아이디어

- [ ] 이미지 제목 + 설명을 알림에 함께 전송 (우주 지식 학습)
- [ ] 주중/주말 배경화면 스케줄 분리
- [ ] 좋아하는 APOD를 구글 포토에 자동 백업
- [ ] Notion 데이터베이스에 날짜별 APOD 아카이브
- [ ] 이미지 품질 필터링
