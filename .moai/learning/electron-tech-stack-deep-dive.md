# Electron + PyInstaller Tech Stack Deep Dive

## Executive Summary

이 문서는 KR Stock Screener 프로젝트를 Electron 데스크톱 앱으로 마이그레이션하기 위한 **구체적인 기술 스택과 설정**을 다룹니다.

---

## 1. Technology Stack Overview

```
┌─────────────────────────────────────────────────────────────┐
│  electron-builder (Packaging & Distribution)                │
│  └── electron-vite (Build Tool)                             │
│      └── vite-plugin-electron (Vite + Electron Integration) │
│          ├── Main Process (Node.js)                         │
│          ├── Renderer Process (React + TypeScript)          │
│          └── Preload Scripts (IPC Bridge)                   │
└─────────────────────────────────────────────────────────────┘
                           │ spawn
┌─────────────────────────────────────────────────────────────┐
│  PyInstaller (Python Bundling)                              │
│  └── FastAPI Backend                                        │
│      ├── my_chart package                                   │
│      ├── fnguide package                                    │
│      └── LangChain (future)                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Project Structure

### 2.1 Recommended Directory Layout

```
kr-stock-screener/
├── electron/                    # Electron-specific code
│   ├── main.ts                 # Main process entry
│   ├── preload.ts              # Preload scripts (IPC bridge)
│   └── electron-env.d.ts       # TypeScript declarations
│
├── src/                        # React frontend (기존 frontend/src)
│   ├── App.tsx
│   ├── components/
│   └── ...
│
├── backend/                    # Python backend (기존 그대로)
│   ├── main.py
│   ├── routers/
│   └── ...
│
├── electron-builder.yml        # Build configuration
├── electron.vite.config.ts     # Vite + Electron config
├── pyproject.toml              # Python dependencies
└── package.json                # Node.js dependencies
```

### 2.2 package.json Configuration

```json
{
  "name": "kr-stock-screener",
  "version": "1.0.0",
  "main": "dist-electron/main.js",
  "scripts": {
    "dev": "electron-vite dev",
    "build": "electron-vite build",
    "preview": "electron-vite preview",
    "build:python": "pyinstaller backend.spec",
    "build:all": "npm run build:python && npm run build && electron-builder",
    "postinstall": "electron-builder install-app-deps"
  },
  "dependencies": {
    "electron-updater": "^6.1.7"
  },
  "devDependencies": {
    "@electron-toolkit/preload": "^3.0.1",
    "@electron-toolkit/utils": "^3.0.0",
    "electron": "^33.2.0",
    "electron-builder": "^25.1.8",
    "electron-vite": "^2.3.0",
    "vite": "^6.0.0",
    "vite-plugin-electron": "^0.29.0",
    "vite-plugin-electron-renderer": "^0.14.6"
  }
}
```

---

## 3. Electron Main Process

### 3.1 Basic Main Process (electron/main.ts)

```typescript
import { app, BrowserWindow, ipcMain } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { spawn, ChildProcess } from 'child_process'

let pythonProcess: ChildProcess | null = null
let mainWindow: BrowserWindow | null = null

// Python Backend 실행
function startPythonBackend(): Promise<number> {
  return new Promise((resolve, reject) => {
    const isDev = is.dev
    const backendPath = isDev
      ? join(__dirname, '../../backend/main.py')
      : join(process.resourcesPath, 'backend', 'backend')

    // 개발 모드: uvicorn 직접 실행
    if (isDev) {
      pythonProcess = spawn('uvicorn', ['backend.main:app', '--port', '8000'], {
        cwd: join(__dirname, '../../'),
        stdio: 'inherit'
      })
    } else {
      // 프로덕션: PyInstaller 번들 실행
      pythonProcess = spawn(backendPath, [], {
        stdio: 'inherit'
      })
    }

    pythonProcess.on('error', (err) => {
      console.error('Python backend failed to start:', err)
      reject(err)
    })

    // 백엔드 시작 대기
    setTimeout(() => resolve(8000), 2000)
  })
}

// IPC 핸들러: Python 백엔드 상태 확인
ipcMain.handle('backend:status', () => {
  return pythonProcess !== null && !pythonProcess.killed
})

// IPC 핸들러: Python 백엔드 재시작
ipcMain.handle('backend:restart', async () => {
  if (pythonProcess) {
    pythonProcess.kill()
  }
  return startPythonBackend()
})

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  // 개발 모드: Vite dev server
  // 프로덕션: 빌드된 React 파일
  if (is.dev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// 앱 시작
app.whenReady().then(async () => {
  // macOS app menu
  electronApp.setAppUserModelId('com.yourcompany.krstockscreener')

  // 개발 모드 단축키 최적화
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // Python 백엔드 시작
  try {
    await startPythonBackend()
    console.log('Python backend started on port 8000')
  } catch (err) {
    console.error('Failed to start Python backend:', err)
    app.quit()
    return
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

// 앱 종료 시 Python 프로세스 정리
app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill()
  }
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('quit', () => {
  if (pythonProcess) {
    pythonProcess.kill()
  }
})
```

### 3.2 Preload Script (electron/preload.ts)

```typescript
import { contextBridge, ipcRenderer } from 'electron'

// Renderer Process에 노출할 API
const electronAPI = {
  // Python 백엔드 상태 확인
  getBackendStatus: () => ipcRenderer.invoke('backend:status'),

  // Python 백엔드 재시작
  restartBackend: () => ipcRenderer.invoke('backend:restart'),

  // 플랫폼 정보
  platform: process.platform,

  // 앱 버전
  appVersion: process.env.npm_package_version || '1.0.0'
}

// Context Bridge로 안전하게 노출
contextBridge.exposeInMainWorld('electronAPI', electronAPI)

// TypeScript 타입 정의
export type ElectronAPI = typeof electronAPI
```

### 3.3 TypeScript Declaration (electron/electron-env.d.ts)

```typescript
import { ElectronAPI } from './preload'

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}

export {}
```

---

## 4. PyInstaller Configuration

### 4.1 Spec File (backend.spec)

```python
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# 프로젝트 루트 경로
project_root = Path(SPECPATH).parent

a = Analysis(
    ['backend/main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # 데이터 파일 포함
        ('data/*.db', 'data'),
        ('sectormap.xlsx', '.'),
        # 패키지 소스 포함 (디버깅용)
        ('my_chart', 'my_chart'),
        ('fnguide', 'fnguide'),
    ],
    hiddenimports=[
        # FastAPI 관련
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',

        # SSE 관련
        'sse_starlette',
        'sse_starlette.sse',

        # pykrx 관련
        'pykrx',
        'pykrx.stock',

        # pandas 관련
        'pandas',
        'pandas._libs',
        'pandas._libs.tslibs',

        # 기타
        'requests',
        'numpy',
        'openpyxl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # 미사용
        'mplfinance',  # 미사용
        'tkinter',     # 미사용
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # UPX 압축 사용
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 디버깅용, 프로덕션은 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### 4.2 Build Script (scripts/build-backend.sh)

```bash
#!/bin/bash

# Python 백엔드 빌드 스크립트

set -e

echo "Building Python backend with PyInstaller..."

# 가상 환경 활성화
source .venv/bin/activate

# PyInstaller 실행
pyinstaller backend.spec --clean

# 빌드 결과 확인
if [ -f "dist/backend" ]; then
    echo "✓ Python backend built successfully: dist/backend"
    ls -lh dist/backend
else
    echo "✗ Build failed"
    exit 1
fi
```

---

## 5. electron-builder Configuration

### 5.1 electron-builder.yml

```yaml
appId: com.yourcompany.krstockscreener
productName: KR Stock Screener
copyright: Copyright © 2026 Your Company

# 빌드된 파일
files:
  - dist/**/*
  - dist-electron/**/*
  - package.json

# 추가 리소스 (Python 백엔드)
extraResources:
  - from: "dist/backend"
    to: "backend"
    filter:
      - "**/*"

# 데이터베이스 파일
extraFiles:
  - from: "data"
    to: "data"
    filter:
      - "*.db"

# 디렉토리 설정
directories:
  buildResources: build
  output: release

# macOS 설정
mac:
  category: public.app-category.finance
  hardenedRuntime: true
  gatekeeperAssess: false
  entitlements: build/entitlements.mac.plist
  entitlementsInherit: build/entitlements.mac.plist
  target:
    - target: dmg
      arch:
        - x64
        - arm64
    - target: zip
      arch:
        - x64
        - arm64

# Windows 설정
win:
  target:
    - target: nsis
      arch:
        - x64
    - target: portable
      arch:
        - x64
  signingHashAlgorithms:
    - sha256

# Linux 설정
linux:
  target:
    - target: AppImage
      arch:
        - x64
    - target: deb
      arch:
        - x64
  category: Office
  maintainer: your@email.com

# NSIS 설치 프로그램 설정
nsis:
  oneClick: false
  perMachine: false
  allowToChangeInstallationDirectory: true
  deleteAppDataOnUninstall: false

# DMG 설정
dmg:
  writeUpdateInfo: true
  artifactName: ${name}-${version}-${arch}.${ext}

# 자동 업데이트
publish:
  - provider: github
    owner: your-username
    repo: kr-stock-screener
```

### 5.2 macOS Entitlements (build/entitlements.mac.plist)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
  </dict>
</plist>
```

---

## 6. Vite + Electron Configuration

### 6.1 electron.vite.config.ts

```typescript
import { resolve } from 'path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'
import svgr from 'vite-plugin-svgr'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    resolve: {
      alias: {
        '@': resolve('src')
      }
    },
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'electron/main.ts')
        }
      }
    }
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    resolve: {
      alias: {
        '@': resolve('src')
      }
    },
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'electron/preload.ts')
        }
      }
    }
  },
  renderer: {
    plugins: [react(), svgr()],
    resolve: {
      alias: {
        '@': resolve('src')
      }
    },
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'index.html')
        }
      }
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true
        }
      }
    }
  }
})
```

---

## 7. React Integration

### 7.1 Frontend API Client (src/api/client.ts)

```typescript
import axios from 'axios'

// 개발 모드: Vite proxy 사용
// 프로덕션: 직접 localhost:8000 호출
const API_BASE_URL = import.meta.env.DEV
  ? '/api'
  : 'http://localhost:8000/api'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Electron 환경에서 백엔드 상태 확인
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await apiClient.get('/db/last-updated')
    return response.status === 200
  } catch {
    return false
  }
}

// 백엔드 재시작 (Electron 전용)
export async function restartBackend(): Promise<void> {
  if (window.electronAPI) {
    await window.electronAPI.restartBackend()
  }
}
```

### 7.2 React Hook for Backend Status (src/hooks/useBackendStatus.ts)

```typescript
import { useEffect, useState } from 'react'
import { checkBackendHealth } from '@/api/client'

export function useBackendStatus() {
  const [isHealthy, setIsHealthy] = useState(false)
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    const checkStatus = async () => {
      setIsChecking(true)
      const healthy = await checkBackendHealth()
      setIsHealthy(healthy)
      setIsChecking(false)
    }

    checkStatus()

    // 30초마다 상태 확인
    const interval = setInterval(checkStatus, 30000)

    return () => clearInterval(interval)
  }, [])

  return { isHealthy, isChecking }
}
```

---

## 8. Build & Release Pipeline

### 8.1 GitHub Actions Workflow (.github/workflows/release.yml)

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-python:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]
        include:
          - os: macos-latest
            platform: macos
          - os: windows-latest
            platform: windows
          - os: ubuntu-latest
            platform: linux

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install Python Dependencies
        run: |
          python -m venv .venv
          source .venv/bin/activate  # Linux/macOS
          # .venv\Scripts\activate  # Windows
          pip install -e .
          pip install pyinstaller

      - name: Build Python Backend
        run: |
          source .venv/bin/activate
          pyinstaller backend.spec --clean

      - name: Upload Python Artifact
        uses: actions/upload-artifact@v4
        with:
          name: backend-${{ matrix.platform }}
          path: dist/backend

  build-electron:
    needs: build-python
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Download Python Artifact
        uses: actions/download-artifact@v4
        with:
          name: backend-${{ matrix.platform }}
          path: dist/backend

      - name: Install Node Dependencies
        run: npm ci

      - name: Build Electron App
        run: npm run build && electron-builder --publish always
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 9. Development Workflow

### 9.1 Local Development

```bash
# 1. Python 백엔드 실행 (터미널 1)
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# 2. Electron 개발 모드 실행 (터미널 2)
npm run dev
```

### 9.2 Production Build

```bash
# 1. Python 백엔드 빌드
./scripts/build-backend.sh

# 2. Electron 앱 빌드
npm run build:all
```

### 9.3 Testing Built App

```bash
# 빌드된 앱 실행 (macOS)
open release/mac-arm64/KR Stock Screener.app

# Windows
release\win-unpacked\KR Stock Screener.exe

# Linux
release/linux-unpacked/kr-stock-screener
```

---

## 10. Troubleshooting

### 10.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Python process won't start | Path issue | Use `process.resourcesPath` for production |
| Port 8000 already in use | Another process using port | Kill existing process or use dynamic port |
| PyInstaller missing modules | Hidden imports missing | Add to `hiddenimports` in spec file |
| macOS code signing fails | Missing entitlements | Check `entitlements.mac.plist` |
| Windows SmartScreen warning | Unsigned executable | Purchase code signing certificate |

### 10.2 Debug Mode

```typescript
// electron/main.ts - 개발 모드에서만 로그 출력
if (is.dev) {
  pythonProcess = spawn('uvicorn', ['backend.main:app', '--port', '8000', '--log-level', 'debug'], {
    cwd: join(__dirname, '../../'),
    stdio: 'inherit'
  })
}
```

---

## 11. Performance Optimization

### 11.1 Lazy Loading Python Backend

```typescript
// electron/main.ts
let backendStarted = false

ipcMain.handle('backend:ensure-started', async () => {
  if (!backendStarted) {
    await startPythonBackend()
    backendStarted = true
  }
  return true
})
```

### 11.2 Bundle Size Reduction

```python
# backend.spec - 불필요한 모듈 제외
excludes=[
    'matplotlib',
    'mplfinance',
    'tkinter',
    'unittest',
    'test',
    'tests',
]
```

---

## 12. Security Considerations

### 12.1 Context Isolation

```typescript
// Always enable context isolation
webPreferences: {
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: true  // 가능한 경우
}
```

### 12.2 IPC Validation

```typescript
// electron/main.ts
import { validateIpcMessage } from './ipc-validator'

ipcMain.handle('backend:restart', async (event, ...args) => {
  if (!validateIpcMessage(event)) {
    throw new Error('Invalid IPC message')
  }
  // ... 기존 로직
})
```

---

Version: 1.0.0
Last Updated: 2026-03-06
Author: Yoda (MoAI-ADK)
Related: electron-migration-feasibility.md
