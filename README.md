# LOL Team Builder

리그 오브 레전드 내전 팀 밸런싱을 위한 데스크톱 클라이언트와 FastAPI 서버를 함께 관리하는 저장소입니다.

## 프로젝트 구성

- `client/`
  데스크톱 클라이언트 소스, UI 모듈, 실행 스크립트, 로컬 데이터, PyInstaller 설정이 들어 있습니다.
- `client/main.py`
  클라이언트 실행 진입점입니다.
- `client/tools/riot_loader.py`
  Riot 계정 및 최근 경기 데이터를 수동 또는 저장 계정 기준으로 적재하는 도구입니다.
- `server/`
  FastAPI 서버 소스와 백엔드 모듈이 들어 있습니다.
- `server/main.py`
  로컬 개발용 서버 실행 진입점입니다.
- `patch_notes/`
  날짜별 패치노트를 보관하는 디렉토리입니다.

## 주요 기능

- 10명을 기반으로 밸런스 있는 5:5 팀을 생성합니다.
- 최근 경기 전적을 불러와 승률, KDA, 포지션 통계, 챔피언 통계를 확인할 수 있습니다.
- 최근 폼과 포지션 적합도를 팀 계산에 반영합니다.
- 라인 밸런스 경고와 완화 규칙 적용 여부를 함께 안내합니다.
- Riot API 기반 데이터 적재 도구로 계정 및 경기 데이터를 저장할 수 있습니다.

## 실행 가이드

### 클라이언트 실행

```bash
python client/main.py
```

### Riot 데이터 로더 실행

```bash
python -m client.tools.riot_loader
```

### 서버 실행

```bash
python -m uvicorn server.main:app --reload
```

### 클라이언트 빌드

```bash
pyinstaller client/main.spec
```

## 데이터 및 빌드 산출물

- 클라이언트 런타임 데이터는 `client/data/` 아래에 저장됩니다.
- 빌드 산출물인 `dist/`와 클라이언트 에러 로그는 Git 추적 대상에서 제외됩니다.
