---
name: moai-library-tradingview
description: >
  TradingView 차트 라이브러리 전문 스킬 (Next.js). Lightweight Charts (오픈소스 npm)와
  TradingView Advanced Charts (charting_library)를 모두 커버.
  캔들스틱/라인/에리어 차트, 실시간 데이터 스트리밍, 커스텀 datafeed API,
  Next.js dynamic import 패턴을 제공.
  Use when building TradingView-style charts, stock charts, financial charts,
  candlestick charts, or integrating tradingview lightweight-charts in React/Next.js.
license: Apache-2.0
compatibility: Designed for Claude Code
allowed-tools: Read, Grep, Glob, WebFetch, WebSearch
user-invocable: false
metadata:
  version: "1.0.0"
  category: "library"
  status: "active"
  updated: "2026-02-27"
  modularized: "false"
  tags: "tradingview, lightweight-charts, charting, candlestick, stock chart, nextjs, react, financial"
  related-skills: "moai-lang-typescript, moai-domain-frontend"

# MoAI Extension: Progressive Disclosure
progressive_disclosure:
  enabled: true
  level1_tokens: 100
  level2_tokens: 5000

# MoAI Extension: Triggers
triggers:
  keywords: ["tradingview", "lightweight-charts", "candlestick", "stock chart", "financial chart", "charting library", "OHLCV chart", "차트", "캔들스틱", "주가차트"]
  agents: ["expert-frontend"]
  phases: ["run"]
---

## Quick Reference

**Lightweight Charts v5.1.0** (오픈소스, npm 설치 가능) / **TradingView Advanced Charts** (charting_library, 별도 접근 필요)

### 핵심 규칙 - Next.js에서 반드시 지켜야 할 것

[HARD] `dynamic import + ssr: false` 없이는 절대 작동하지 않음. 두 라이브러리 모두 브라우저 전용 Canvas API를 사용하므로 SSR에서 크래시 발생.

[HARD] `useEffect` + `useRef` 패턴으로 마운트. cleanup 함수에서 반드시 `chart.remove()` 호출해야 메모리 누수 방지.

### 설치 (Lightweight Charts)

```bash
npm install lightweight-charts
```

### 지원 차트 타입

- `CandlestickSeries` - OHLCV 캔들스틱
- `LineSeries` - 라인
- `AreaSeries` - 에리어 (그라데이션 채움)
- `BarSeries` - 바 차트
- `HistogramSeries` - 히스토그램 (거래량 등)
- `BaselineSeries` - 기준선 대비 상/하

---

## Implementation Guide

### 1. Next.js App Router - 기본 캔들스틱 차트

**컴포넌트 파일** (`components/CandlestickChart.tsx`):

```tsx
'use client';

import { useEffect, useRef } from 'react';
import {
  createChart,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickSeriesOptions,
  type Time,
} from 'lightweight-charts';

interface OHLCVData {
  time: Time;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface CandlestickChartProps {
  data: OHLCVData[];
  width?: number;
  height?: number;
}

export function CandlestickChart({ data, width = 800, height = 400 }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // 차트 생성
    chartRef.current = createChart(containerRef.current, {
      width,
      height,
      layout: {
        background: { color: '#1a1a2e' },
        textColor: '#d1d5db',
      },
      grid: {
        vertLines: { color: '#2d2d44' },
        horzLines: { color: '#2d2d44' },
      },
      timeScale: {
        borderColor: '#485c7b',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // 시리즈 추가
    seriesRef.current = chartRef.current.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    } as CandlestickSeriesOptions);

    seriesRef.current.setData(data);
    chartRef.current.timeScale().fitContent();

    // cleanup - 필수
    return () => {
      chartRef.current?.remove();
      chartRef.current = null;
    };
  }, []);

  // 데이터 업데이트 (차트 재생성 없이)
  useEffect(() => {
    seriesRef.current?.setData(data);
  }, [data]);

  return <div ref={containerRef} />;
}
```

**페이지에서 dynamic import 사용** (`app/chart/page.tsx`):

```tsx
import dynamic from 'next/dynamic';

// SSR 비활성화 - 필수
const CandlestickChart = dynamic(
  () => import('@/components/CandlestickChart').then((m) => m.CandlestickChart),
  { ssr: false, loading: () => <div className="h-96 animate-pulse bg-gray-800" /> }
);

export default function ChartPage() {
  const data = [
    { time: '2024-01-01', open: 100, high: 110, low: 95, close: 105 },
    { time: '2024-01-02', open: 105, high: 115, low: 100, close: 108 },
  ];
  return <CandlestickChart data={data} />;
}
```

### 2. 반응형 리사이즈 처리

```tsx
useEffect(() => {
  if (!containerRef.current || !chartRef.current) return;

  const resizeObserver = new ResizeObserver((entries) => {
    const { width, height } = entries[0].contentRect;
    chartRef.current?.applyOptions({ width, height });
  });

  resizeObserver.observe(containerRef.current);
  return () => resizeObserver.disconnect();
}, []);
```

### 3. 실시간 데이터 스트리밍

```tsx
// 마지막 캔들 업데이트 (틱 단위)
const updateRealtime = (tick: { time: Time; price: number }) => {
  seriesRef.current?.update({
    time: tick.time,
    open: lastCandle.open,
    high: Math.max(lastCandle.high, tick.price),
    low: Math.min(lastCandle.low, tick.price),
    close: tick.price,
  });
};

// WebSocket 연동 예시
useEffect(() => {
  const ws = new WebSocket('wss://your-data-feed');
  ws.onmessage = (e) => {
    const tick = JSON.parse(e.data);
    updateRealtime(tick);
  };
  return () => ws.close();
}, []);
```

### 4. 거래량 히스토그램 + 가격 차트 (멀티 시리즈)

```tsx
// 별도 price scale에 거래량 표시
const volumeSeries = chartRef.current.addSeries(HistogramSeries, {
  color: '#26a69a',
  priceFormat: { type: 'volume' },
  priceScaleId: 'volume', // 별도 스케일
});

chartRef.current.priceScale('volume').applyOptions({
  scaleMargins: { top: 0.8, bottom: 0 }, // 하단 20%에 표시
});
```

### 5. 크로스헤어 커스텀 툴팁

```tsx
chartRef.current.subscribeCrosshairMove((param) => {
  if (!param.time || !param.seriesData) return;

  const candleData = param.seriesData.get(seriesRef.current!);
  if (candleData && 'open' in candleData) {
    // 툴팁 업데이트 로직
    setTooltip({
      time: param.time as string,
      open: candleData.open,
      high: candleData.high,
      low: candleData.low,
      close: candleData.close,
    });
  }
});
```

### 6. TradingView Advanced Charts (charting_library) Next.js 설정

charting_library는 접근 권한이 필요한 별도 패키지입니다.

```tsx
// public/charting_library/ 에 파일 배치 후
import dynamic from 'next/dynamic';

const TVChart = dynamic(() => import('@/components/TVChartContainer'), { ssr: false });

// components/TVChartContainer.tsx
'use client';
import { useEffect, useRef } from 'react';

declare global {
  interface Window {
    TradingView: {
      widget: new (config: TVWidgetConfig) => TVWidget;
    };
  }
}

export default function TVChartContainer() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const script = document.createElement('script');
    script.src = '/charting_library/charting_library.standalone.js';
    script.onload = () => {
      new window.TradingView.widget({
        container: containerRef.current!,
        locale: 'ko',
        datafeed: new Datafeed(), // 커스텀 datafeed 구현 필요
        library_path: '/charting_library/',
        symbol: 'AAPL',
        interval: 'D',
        fullscreen: false,
        autosize: true,
      });
    };
    document.head.appendChild(script);
  }, []);

  return <div ref={containerRef} style={{ height: '600px' }} />;
}
```

---

## Advanced Patterns

### 데이터 포맷 요구사항

```typescript
// time 필드는 반드시 UTC 기준 UNIX timestamp (초) 또는 'YYYY-MM-DD' 문자열
type Time = UTCTimestamp | BusinessDay | string;

// UNIX timestamp 사용 시 (초 단위, 밀리초 아님)
const data = [
  { time: 1704067200 as UTCTimestamp, open: 100, high: 110, low: 95, close: 105 },
];

// 시간 포함 데이터는 반드시 timeVisible: true 설정 필요
```

### 알려진 이슈 (v5.1.0 기준 GitHub 오픈 이슈)

- **시리즈 대량 삭제 성능** (#2049): 수백 개 이상의 시리즈를 한번에 제거하면 메인 스레드 블로킹 2-4초 발생. 타임프레임 전환 시 주의.
- **fixLeftEdge + fixRightEdge 동시 사용** (#2044): null 값과 함께 사용 시 마우스 hover에서 에러 발생.
- **Ionic/크롬 시뮬레이터** (#2046): Chrome Mobile Simulator 확장과 충돌 가능.
- **navigator.userAgentData** (#2058): 일부 브라우저에서 undefined. v5.1.0에서 fallback 처리됨.

### v5.1.0 새 기능: Data Conflation

```typescript
// 대용량 데이터셋 렌더링 성능 개선
createChart(container, {
  // 기본값은 false
  enableConflation: true,
  conflationThresholdFactor: 2, // 줌아웃 시 병합 임계값
  precomputeConflationOnInit: true, // 초기화 시 사전 계산
});
```

### TypeScript 타입 가이드

```typescript
import type {
  IChartApi,           // 차트 인스턴스
  ISeriesApi,          // 시리즈 인스턴스 (제네릭)
  Time,                // 타임스탬프 타입
  UTCTimestamp,        // UNIX 타임스탬프
  BusinessDay,         // { year, month, day }
  CandlestickData,     // OHLCV 데이터
  LineData,            // { time, value }
  HistogramData,       // { time, value, color? }
  ChartOptions,        // createChart 옵션
  DeepPartial,         // 부분 옵션 타입
} from 'lightweight-charts';
```

### Pages Router에서 사용 시

```tsx
// pages/chart.tsx
import dynamic from 'next/dynamic';

const Chart = dynamic(() => import('../components/CandlestickChart'), {
  ssr: false,
});

export default function ChartPage() {
  return <Chart data={[]} />;
}
```

---

## Works Well With

- **moai-lang-typescript**: TypeScript 타입 안전성 강화
- **moai-domain-frontend**: React/Next.js 컴포넌트 아키텍처
- **moai-library-shadcn**: 차트 주변 UI 컴포넌트 (툴바, 패널 등)

### 공식 문서

- Lightweight Charts 문서: tradingview.github.io/lightweight-charts/
- GitHub: github.com/tradingview/lightweight-charts
- charting_library 예시: github.com/tradingview/charting-library-examples

---

Last Updated: 2026-02-27
Version: 1.0.0 (Lightweight Charts v5.1.0 기준)
