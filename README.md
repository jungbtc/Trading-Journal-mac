# 온체인 매매일지 — Mac 앱

코인 지갑과 거래소 내역을 모아 매매일지를 보여 주는 독립 실행형 Mac 앱입니다. DMG를 받아 응용 프로그램 폴더에 넣고 실행하면 됩니다. 매매일지를 사용하는 데 터미널, Python, Node 설치나 코딩은 필요하지 않습니다.

**원작:** [extb001-afk](https://github.com/extb001-afk)와 tj-bot 기여자들이 만든 [Trading-Journal](https://github.com/extb001-afk/Trading-Journal)입니다. 매매일지 계산 로직, 대시보드, 각종 연동 기능은 원작자들의 작업입니다. 이 저장소에서는 Mac 창, 실행 환경 내장, 시작·종료 처리, DMG 배포 기능을 추가했습니다.

## 다운로드와 설치

**[최신 Mac 버전 다운로드](https://github.com/jungbtc/Trading-Journal-mac/releases/latest)**

1. 릴리스 페이지 아래 **Assets**에서 `.dmg` 파일을 받습니다.
2. DMG를 열고 **Trading Journal**을 **응용 프로그램(Applications)** 폴더로 끌어 놓습니다.
3. 응용 프로그램 폴더에서 **Trading Journal**을 실행합니다.
4. 매매일지 비밀번호를 만듭니다. 처음 실행할 때 필요한 설정 코드는 앱이 자동으로 입력합니다.
5. 설정 마법사에서 지갑 주소와 제공업체·거래소의 **조회 전용 API 키**를 추가합니다.

**macOS 12 Monterey 이상**, **Apple Silicon과 Intel Mac**을 지원하는 유니버설 앱입니다. Python은 앱에 들어 있습니다. 실제 데이터를 동기화하려면 인터넷 연결과 본인의 제공업체·거래소 키가 필요합니다.

릴리스 설명에서 서명·공증 상태를 확인할 수 있습니다. Developer ID 서명은 배포자를 확인하는 절차이며, Apple 공증은 제출된 앱 패키지를 검사하는 절차입니다. 이 절차가 매매일지 계산 결과의 정확성을 보증하는 것은 아닙니다.

## 포함된 기능

- 원본의 지갑·거래소 수집기, 로컬 SQLite 원장, 대시보드
- 원가, 실현·미실현 손익, 과거 기록, 명세 내보내기
- 원본의 NFT, Hyperliquid, 기타 자산, 텔레그램 연동 코드
- 복사·붙여넣기, 파일 저장·선택을 지원하는 Mac 창
- 초기 설정 자동화, 로컬 데이터 권한 설정, 로그 정리, 정상 종료 처리
- Mac 메뉴의 데이터 폴더 열기(**Open Data Folder**), 로그 열기(**Open Logs**), 로그인 비밀번호 초기화(**Reset Login Password**)

![원본 대시보드 — 금액은 가려진 예시입니다](docs/screenshots/01_dashboard_top.png)

원본 프로젝트의 화면이며 금액은 가려져 있습니다. 전체 기능 설명과 원본의 주의사항은 [원본 문서](README.upstream.md)를 확인하세요.

## 내 데이터는 어디에 저장되나요?

설정, 비밀번호, 제공업체 키, 매매일지는 이 Mac의 다음 폴더에 저장됩니다.

```text
~/Library/Application Support/Trading Journal/
```

앱 메뉴에서 **Trading Journal > Open Data Folder**를 선택하면 폴더를 열 수 있습니다. 대시보드는 이 Mac에서만 접속할 수 있습니다. 앱을 교체하거나 삭제해도 데이터 폴더는 남습니다. 배포 파일에는 개인 매매일지, 지갑, 비밀번호, API 키가 들어 있지 않습니다.

**동기화하려면 앱을 열어 두세요.** 마지막 창을 닫거나 앱을 종료하면 모든 매매일지 서비스가 멈춥니다. 자동 로컬 백업도 앱이 실행 중일 때 동작할 수 있습니다. 데이터 폴더는 별도로 백업하고, 친구에게는 데이터 폴더 대신 DMG만 보내세요.

비밀번호를 잊었다면 **Trading Journal > Reset Login Password**를 선택하세요. 매매일지와 제공업체 키는 그대로 남습니다.

## 현재 버전의 제한

- **Claude AI는 선택 기능이며 기본으로 꺼져 있습니다.** 원본과 같은 기본값입니다. Claude Code는 내장되어 있지 않으며, 코딩 없이 Claude를 설정하는 화면과 일간·주간 리뷰 작업 실행 기능은 아직 없습니다. 다른 AI 기능도 별도로 설치·로그인한 Claude CLI와 해당 설정이 필요합니다.
- 앱을 종료한 뒤의 백그라운드 동기화, 로그인 시 자동 실행, 앱 내 업데이트 기능은 없습니다. 업데이트하려면 앱을 종료하고 새 DMG를 설치하세요.
- 이 Mac에서만 접속하도록 설정됩니다. 원본의 선택 기능인 LAN·Tailscale 접속 설정은 앱에서 제공하지 않습니다.
- 수집기의 자식 프로세스 복구 기능은 포함되어 있습니다. 상위 서비스가 종료되면 앱을 다시 열어야 합니다. 일부 상세 상태 진단은 아직 PM2 로그를 기준으로 동작합니다.
- 복원, 외부 백업 예약, 데모, 고급 복구 도구는 소스에 포함되어 있지만 Mac 앱에서 누를 수 있는 버튼은 아직 없습니다.
- 이 Mac 배포본은 실제 계정 키를 사용한 지갑·거래소·Claude 연결 시험을 하지 않았습니다. 원본에서도 증권사 연동은 미검증으로 안내합니다.

이 배포본은 기존 프로젝트를 Mac 앱으로 포장한 버전입니다. 합계 금액을 활용하기 전에 원본 문서의 계산 한계와 추정 데이터 표시를 확인하세요.

## 개발과 검증

개발자를 위한 빌드·서명·공증·검증 방법은 [macos/README.md](macos/README.md)에 있습니다. 원본 실행 코드는 버전 `2026.10.12.8`, 커밋 [`8e9a70c2d7d47dbf59d9afd067946d9d8484b9ab`](https://github.com/extb001-afk/Trading-Journal/commit/8e9a70c2d7d47dbf59d9afd067946d9d8484b9ab)을 기준으로 포함했습니다.

첫 실행, 포트 충돌, 개인 파일 권한, 중복 실행 방지, 비밀번호 설정·초기화, 화면 파일, 데이터 유지, 서비스 종료를 확인했습니다. Apple Silicon과 Intel 실행 환경을 모두 검사했으며, 개발 Mac에서의 Intel 검사는 Rosetta로 진행했습니다. 내장 Python으로 원본 인증 시험 31개도 통과했습니다.

## 원작자와 라이선스

- **[extb001-afk](https://github.com/extb001-afk)와 tj-bot 기여자:** 매매일지 계산 로직과 대시보드를 포함한 원본 [Trading-Journal](https://github.com/extb001-afk/Trading-Journal)
- **[jungbtc](https://github.com/jungbtc):** Mac 앱 포장과 배포
- **[Astral Python Build Standalone](https://github.com/astral-sh/python-build-standalone):** 내장 Python 3.12.14 실행 환경, 릴리스 `20260901`

[MIT 라이선스](LICENSE)로 배포하며 원본 저작권 고지를 포함합니다. Python과 의존 구성요소의 라이선스 고지는 [macos/licenses](macos/licenses)와 앱 안에 있습니다.

## 후원과 문의

**후원은 언제나 환영합니다.** Mac 앱 포장과 유지보수에 도움을 주고 싶다면 **[buymeacoffee.com/jungjung](https://buymeacoffee.com/jungjung)**에서 후원할 수 있습니다.

Mac 배포 관련 문제는 [이 저장소의 Issues](https://github.com/jungbtc/Trading-Journal-mac/issues)에 알려 주세요. 원본 프로젝트의 공로는 원작자와 기여자들에게 있습니다.
