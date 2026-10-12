# Mac 앱 개발 안내

원본 매매일지 서비스와 대시보드에 AppKit·WebKit 창과 Python 3.12.14 실행 환경을 내장한 유니버설 Mac 앱입니다. macOS 12 이상이 필요합니다. 사용자는 DMG로 설치하며 Python, Node, 터미널, 개발 도구를 설치할 필요가 없습니다.

## 빌드

개발용 Mac에는 Command Line Tools와 Python 3.9 이상이 필요합니다.

```sh
python3 macos/build.py
```

지정된 버전의 Astral 실행 환경 두 개를 받아 SHA-256을 확인하고, Apple Silicon·Intel용 창 프로그램을 컴파일합니다. 앱을 서명한 뒤 `dist/Trading-Journal-1.0.1-universal.dmg`를 만들고 검사합니다. 실행 환경의 라이선스 고지는 `macos/licenses`에 있습니다. 원본 소스 기준 커밋은 `8e9a70c`입니다.

## 서명과 Apple 공증

별도 설정이 없으면 앱과 DMG에 임시 서명(ad-hoc)을 적용합니다. Developer ID 배포본을 만들려면 빌드할 때 `CODE_SIGN_IDENTITY`에 Mac에 설치된 Developer ID Application 인증서 이름을 지정하세요.

빌드 스크립트는 내부 실행 파일부터 순서대로 강화된 실행 환경(hardened runtime)과 보안 타임스탬프를 적용하고, 앱과 DMG를 서명합니다. Python 실행 파일에만 ctypes·libffi 콜백에 필요한 실행 메모리 권한을 부여합니다.

완성된 DMG는 저장된 키체인 프로필을 이용해 `xcrun notarytool submit`으로 제출하세요. **Accepted** 결과를 확인한 뒤 `xcrun stapler`로 공증 티켓을 첨부하고 검증합니다. 티켓 첨부 후에는 SHA-256 체크섬을 다시 만드세요.

서명 키와 공증 인증 정보는 키체인에 보관하고 저장소에는 넣지 마세요. 자세한 절차는 [Apple 공증 문서](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)를 참고하세요.

## 검증

```sh
"dist/Trading Journal.app/Contents/Resources/runtime-arm64/bin/python3" -B macos/test_desktop.py "dist/Trading Journal.app/Contents/Resources/app"
arch -x86_64 "dist/Trading Journal.app/Contents/Resources/runtime-x86_64/bin/python3" -B macos/test_desktop.py "dist/Trading Journal.app/Contents/Resources/app"
```

Intel 검사는 Intel Mac 또는 Rosetta가 설치된 Apple Silicon Mac에서 실행합니다. 임시 데이터를 이용해 첫 실행 인증, 화면 파일, 포트 충돌, 중복 실행, 개인 파일 권한, 데이터 유지, 비밀번호 초기화, 프로세스 종료를 확인합니다.

원본 인증 시험도 내장 실행 환경으로 실행할 수 있습니다.

```sh
"dist/Trading Journal.app/Contents/Resources/runtime-arm64/bin/python3" -B tests/run_all.py http_auth preauth_body
```

## 데이터와 실행 방식

사용자 데이터는 `~/Library/Application Support/Trading Journal`에 저장됩니다. 실행할 때 잠금을 확보한 뒤 이 폴더의 리소스 연결을 갱신하므로, 앱을 옮기거나 업데이트해도 매매일지는 유지됩니다.

수집기는 원본 `unit_runner.py`를 사용합니다. 종료할 때 관련 프로세스 그룹을 멈춘 뒤 창을 닫습니다. 창 프로세스가 비정상 종료된 경우에도 부모 프로세스의 상태를 확인해 서비스를 멈춥니다. 사용자 설정과 데이터는 배포 파일에 복사하지 않습니다.
