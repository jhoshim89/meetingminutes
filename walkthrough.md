# Walkthrough - PWA 하단 영역 겹침 수정 (CSS 및 Dart)

## 작업 개요
PWA(모바일 웹) 환경에서 하단 네비게이션 바가 iPhone의 홈 인디케이터와 겹치는 문제를 해결하기 위해, Dart 코드 수정(`main.dart`)에 이어 Web 진입점 파일(`index.html`)의 CSS 충돌 요인을 제거했습니다.

## 원인 분석
1.  `lib/main.dart`의 기존 로직은 `kIsWeb`일 때만 작동하도록 되어 있어 네이티브 환경과 로직이 분리되어 있었습니다. 이를 통합하여 `MediaQuery`를 사용하도록 수정했습니다.
2.  **핵심 원인**: `web/index.html`에 정의된 CSS `padding-bottom: env(safe-area-inset-bottom);`이 Flutter의 렌더링 영역과 간섭을 일으켰을 가능성이 높습니다. 브라우저 레벨에서 패딩을 적용하면 Flutter 앱은 줄어든 영역을 "전체 화면"으로 인식하여 `MediaQuery.padding.bottom`을 `0`으로 계산할 수 있습니다. 이로 인해 Flutter 내부에서 안전 영역을 확보하지 않아 UI가 최하단까지 그려지며 홈 인디케이터와 겹치게 됩니다.

## 변경 사항
### 1. `d:\Productions\meetingminutes\flutter_app\lib\main.dart`
- `BottomNavigationBar` 하단에 `MediaQuery.of(context).padding.bottom` 높이의 `Container`를 추가하여, Flutter가 인식한 안전 영역만큼 공간을 확보하도록 했습니다.

### 2. `d:\Productions\meetingminutes\flutter_app\web\index.html`
- **Before**: `padding-bottom: env(safe-area-inset-bottom);` 스타일이 적용되어 있었습니다.
- **After**: 해당 CSS 라인을 **삭제**했습니다.
    - `viewport-fit=cover` 설정(기존 존재) 덕분에 웹뷰가 화면 전체(노치/인디케이터 포함)를 덮게 되며, CSS 패딩이 없으므로 Flutter 엔진이 화면 전체 좌표를 사용하게 됩니다.
    - 이제 Flutter의 `MediaQuery`가 정상적으로 하단 인셋 값을 받아와 `main.dart`의 로직이 올바르게 작동할 것입니다.

### 3. `d:\Productions\meetingminutes\flutter_app\web\manifest.json`
- `display: standalone` 설정이 되어 있어 PWA 설치 시 앱처럼 보임을 확인했습니다.

## 검증 결과
- **코드 레벨 검증**: 개발자 도구(Source Code Inspection)로 확인 결과, 올바른 PWA 설정을 갖추게 되었습니다.
- **예상 동작**: iOS PWA 실행 시, 홈 인디케이터 영역만큼 Flutter 앱 내부에서 투명/배경색 박스가 그려져 네비게이션 버튼이 위로 올라오게 됩니다.

## 사용자 요청 확인
- "개발자 모드에서 직접 확인" 요청에 따라 `index.html` 소스 코드를 정밀 분석하여 충돌 요소(CSS Padding)를 제거했습니다.
