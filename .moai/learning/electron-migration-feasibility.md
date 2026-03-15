# Electron Migration Feasibility Analysis

## Executive Summary

**결론**: Electron 마이그레이션은 **가능**하며, 예상 코드 변경률은 **15-20%** 수준입니다.

| 항목 | 평가 | 비고 |
|------|------|------|
| Frontend 재사용 | 100% | React 코드 그대로 사용 |
| Backend 재사용 | 95% | 실행 방식만 변경 |
| LangChain 통합 | 자연스러운 확장 | Python 생태계 유지 |
| 예상 작업 기간 | 4-5주 | 1인 개발 기준 |

---

## 1. Current Architecture Analysis

### 1.1 Present Structure

```
Current Web Application
├── Frontend (React + Vite + TypeScript)
│   └── localhost:5173 → localhost:8000 API 호출
├── Backend (FastAPI + Python 3.13)
│   ├── my_chart package (주식 데이터)
│   ├── fnguide package (재무 분석)
│   └── SQLite databases
└── Communication: HTTP (CORS enabled)
```

### 1.2 Key Dependencies

**Python (Heavy)**:
- pandas, numpy: 데이터 처리
- matplotlib, mplfinance: 차트 생성 (현재 미사용, web은 TradingView)
- pykrx, requests: 외부 API

**JavaScript**:
- React 18, TypeScript
- TradingView Lightweight Charts
- react-window

---

## 2. Electron Architecture Strategy

### 2.1 Recommended: Sidecar Pattern

```
Electron Application
├── Main Process (Node.js)
│   ├── App lifecycle management
│   ├── FastAPI spawn (child_process)
│   └── Window management
│
├── Renderer Process (Chromium)
│   └── React App (기존 코드 그대로)
│       └── localhost:8000 API 호출
│
└── Python Backend (Sidecar Process)
    ├── PyInstaller 번들로 실행
    ├── FastAPI server (port 8000)
    ├── my_chart + fnguide packages
    └── LangChain (future integration)
```

### 2.2 Why Sidecar Pattern?

**장점**:
1. 기존 코드 변경 최소화
2. Python 생태계 100% 활용
3. 디버깅 용이 (독립 프로세스)
4. LangChain 통합 자연스러움

**단점**:
1. 메모리 사용량 증가 (~300MB)
2. 두 프로세스 관리 복잡성
3. 포트 충돌 가능성 (해결 가능)

---

## 3. Migration Roadmap

### Phase 1: Electron Shell (1-2주)

```javascript
// main.js - Electron Main Process
const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let pythonProcess;

function startPythonBackend() {
    const backendPath = path.join(
        process.resourcesPath,
        'backend',  // PyInstaller 번들
        'backend'    // 실행 파일명
    );

    pythonProcess = spawn(backendPath, [], {
        stdio: 'inherit'
    });
}

app.whenReady().then(() => {
    startPythonBackend();

    const win = new BrowserWindow({
        width: 1400,
        height: 900,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    // 개발: Vite dev server
    // 프로덕션: file:// 빌드된 React
    win.loadURL('http://localhost:5173');
});

app.on('quit', () => {
    pythonProcess?.kill();
});
```

### Phase 2: Python Bundling (1주)

```bash
# PyInstaller로 FastAPI 번들링
pyinstaller --onefile \
    --add-data "data:data" \
    --add-data "my_chart:my_chart" \
    --add-data "fnguide:fnguide" \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.protocols \
    backend/main.py
```

**주의사항**:
- pandas, numpy 등 heavy 패키지로 인해 ~150MB 실행 파일 생성
- macOS/Windows/Linux 각각 별도 빌드 필요

### Phase 3: Build Pipeline (1주)

```javascript
// electron-builder.yml
appId: com.yourcompany.krstockscreener
productName: KR Stock Screener

files:
  - dist/**/*
  - backend/dist/backend

extraResources:
  - backend/dist/backend
  - data/*.db

mac:
  category: public.app-category.finance
  target: dmg
  hardenedRuntime: true

win:
  target: nsis

linux:
  target: AppImage
```

### Phase 4: LangChain Integration (1주)

```python
# backend/langchain_agent.py
from langchain.agents import AgentExecutor
from langchain.chat_models import ChatOpenAI

class StockAnalysisAgent:
    """LangChain 기반 주식 분석 에이전트"""

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4")

    async def analyze_with_natural_language(self, query: str, stock_code: str):
        """
        자연어 쿼리로 주식 분석

        예: "삼성전자 최근 실적 추이와 RIM 밸류에이션 분석해줘"
        """
        # fnguide 데이터 조회
        financial_data = analyze_comp(stock_code)

        # LangChain Agent 실행
        response = await self.agent.arun(
            query=query,
            context=financial_data
        )

        return response
```

---

## 4. Bundle Size Analysis

### 4.1 Size Breakdown

| Component | Size | Notes |
|-----------|------|-------|
| Electron Runtime | ~80MB | Chromium + Node.js |
| React + JS | ~5MB | Vite 빌드 |
| Python Runtime (PyInstaller) | ~50MB | Python + dependencies |
| pandas + numpy | ~40MB | Data processing |
| my_chart + fnguide | ~10MB | Business logic |
| SQLite DBs | ~20MB | 데이터 파일 |
| **Total** | **~205MB** | 압축 후 ~80MB |

### 4.2 Optimization Options

1. **Tree Shaking**: 사용하지 않는 pandas 기능 제거
2. **UPX Compression**: 실행 파일 압축 (30% 감소)
3. **Lazy Loading**: LangChain 모델 지연 로드

---

## 5. Deployment Considerations

### 5.1 Code Signing

**macOS**:
- Apple Developer 계정 필요 ($99/년)
- Hardened Runtime 활성화
- Notarization 필수 (10.15+)

**Windows**:
- 코드 서명 인증서 필요 (~$200/년)
- SmartScreen 경고 방지

### 5.2 Auto-Update

```javascript
// electron-updater 통합
const { autoUpdater } = require('electron-updater');

app.on('ready', () => {
    autoUpdater.checkForUpdatesAndNotify();
});
```

---

## 6. Alternative Approaches

### 6.1 Tauri (Rust)

| Aspect | Electron | Tauri |
|--------|----------|-------|
| Bundle Size | ~200MB | ~30MB |
| Python Integration | Sidecar | Sidecar (동일) |
| Learning Curve | 낮음 | 높음 (Rust) |
| Maturity | 높음 | 중간 |

**결론**: Python 백엔드가 지배적이므로 Tauri의 크기 이점이 미미함.

### 6.2 PWA (Progressive Web App)

**장점**: 배포 간소화, 자동 업데이트
**단점**: Python 백엔드 불가, LangChain 통합 어려움

**결론**: LangChain 통합을 위해 부적합.

---

## 7. Risk Assessment

### 7.1 High Risk

1. **PyInstaller 빌드 복잡성**
   - 완화: conda-pack 또는 Nuitka 대안 검토

2. **플랫폼별 테스트 필요**
   - 완화: CI/CD 파이프라인 구축 (GitHub Actions)

### 7.2 Medium Risk

1. **포트 충돌**
   - 완화: 동적 포트 할당 + IPC로 포트 전달

2. **메모리 사용량**
   - 완화: Python 프로세스 지연 시작

### 7.3 Low Risk

1. **React 코드 호환성**: 100% 호환
2. **SQLite 호환성**: 완벽 지원

---

## 8. Recommendations

### 8.1 Immediate Actions

1. **프로젝트 완성 우선**: 현재 Web App으로 완성
2. **아키텍처 문서화**: API 계약 명확화
3. **테스트 커버리지 확보**: 85%+ 유지

### 8.2 Pre-Migration Checklist

- [ ] Frontend-Backend API 계약 확정
- [ ] 모든 환경 변수 설정 파일화
- [ ] PyInstaller 호환성 테스트 (개발 머신)
- [ ] 번들 사이즈 벤치마크 측정

### 8.3 Migration Timeline

```
Week 1-2: Electron Shell + React 통합
Week 3:   PyInstaller 빌드 파이프라인
Week 4:   배포 설정 (코드 서명, auto-update)
Week 5:   LangChain 통합 + 테스트
```

---

## 9. Conclusion

**Electron 마이그레이션은 기술적으로 충분히 가능하며, 예상보다 적은 코드 변경으로 수행할 수 있습니다.**

**핵심 성공 요인**:
1. Sidecar Pattern으로 기존 Python 코드 보존
2. React 코드 100% 재사용
3. LangChain을 Python 백엔드에 자연스럽게 통합

**주요 과제**:
1. PyInstaller 빌드 파이프라인 구축
2. 크로스 플랫폼 테스트
3. 코드 서인 및 배포 설정

**권장사항**: 현재 Web App을 먼저 완성하고, 사용자 피드백을 수집한 후 Electron 마이그레이션을 진행하는 것이 리스크가 가장 적습니다.

---

## 10. Insight Exercises

### Exercise 1: Architecture Decision

현재 프로젝트에서 FastAPI를 Node.js/Express로 재작성하는 것과 PyInstaller Sidecar 방식을 비교하십시오. 각각의 장단점과 예상 작업량을 분석해 보세요.

### Exercise 2: Performance Trade-off

Electron 앱의 메모리 사용량이 300MB+가 될 것으로 예상됩니다. 이것이 사용자 경험에 미칠 영향과 최적화 전략을 제시하십시오.

### Exercise 3: LangChain Integration Design

LangChain Agent가 fnguide 패키지의 데이터를 활용하여 자연어로 주식 분석을 제공하는 구체적인 시나리오를 설계하십시오.

---

Version: 1.0.0
Last Updated: 2026-03-06
Author: Yoda (MoAI-ADK)
Source: User Query Analysis
