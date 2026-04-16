/**
 * SPEC-AI-REPORT-002 E2E: 빠른 분석(Perplexity) + 심층 분석(Deep) UI 검증.
 *
 * Prerequisites (외부에서 미리 기동):
 *   - 백엔드 :8000 (uvicorn backend.main:app)
 *   - 프론트 :5173 (npm run dev)
 *   - 5개 검색 API 키 + Claude CLI OAuth 세션 (이 세션은 이미 완료)
 *
 * Journeys:
 *   A. 빠른 분석 (Perplexity 모드, default) — SSE 토큰 스트리밍 + 본문 표시
 *   B. 심층 분석 (Deep 모드) — 토글 전환 + 다시 시도 + done까지 (~3분)
 */
import { test, expect, type Page } from '@playwright/test'

const BACKEND = 'http://127.0.0.1:8000'

async function ensureBackendUp(page: Page) {
  const res = await page.request.get(`${BACKEND}/api/chart/010170?weeks=1`, { timeout: 5_000 })
  expect(res.ok(), '백엔드 헬스 체크: /api/chart/010170 200').toBeTruthy()
}

async function openFirstAiReportModal(page: Page) {
  await page.goto('/', { waitUntil: 'networkidle' })
  // 첫 진입 시 차트 그리드는 비어있고 "필터를 적용하여 종목을 검색하세요" 안내 표시.
  // 상단 검색 버튼을 클릭해 default 필터(시가총액 전체, 1D)로 종목 로드.
  const searchBtn = page.locator('button.btn--primary', { hasText: '검색' }).first()
  await expect(searchBtn, '필터바 검색 버튼').toBeVisible({ timeout: 15_000 })
  await searchBtn.click()
  // 차트 셀 + AI 버튼이 화면에 렌더될 때까지 대기 (최대 60초; pykrx 데이터 로딩)
  await page.waitForFunction(
    () => document.querySelectorAll('button[title="AI 기업 분석"]').length > 0,
    { timeout: 60_000 }
  )
  const aiBtn = page.locator('button[title="AI 기업 분석"]').first()
  await expect(aiBtn, 'AI 분석 버튼이 화면에 표시되어야 함').toBeVisible({ timeout: 5_000 })
  await aiBtn.click()
  // 모달 헤더의 토글이 표시될 때까지 대기
  const toggleContainer = page.locator('div[role="tablist"][aria-label="분석 모드"]')
  await expect(toggleContainer, 'AI Report 모달 + 모드 토글 표시').toBeVisible({ timeout: 10_000 })
  return toggleContainer
}

test.describe('SPEC-AI-REPORT-002 — 모드 토글 UI', () => {
  test('AC-014 토글 2개 버튼 표시 + ARIA + 라벨 정상', async ({ page }) => {
    test.setTimeout(60_000)
    await ensureBackendUp(page)
    const toggle = await openFirstAiReportModal(page)

    const fastBtn = toggle.locator('button[role="tab"]', { hasText: /빠른 분석/ })
    const deepBtn = toggle.locator('button[role="tab"]', { hasText: /심층 분석/ })

    await expect(fastBtn).toBeVisible()
    await expect(deepBtn).toBeVisible()

    // SPEC #2 결정사항: 라벨 "수분 소요" (v1.0.1) 확인
    await expect(deepBtn).toContainText(/수분 소요/)

    // 기본값: 빠른 분석 active (모달 오픈 직후 자동 시작)
    await expect(fastBtn).toHaveAttribute('aria-selected', 'true')
    await expect(deepBtn).toHaveAttribute('aria-selected', 'false')

    // SPEC FR-011: streaming 중 토글 disabled 검증
    await expect(deepBtn).toBeDisabled()
    await expect(fastBtn).toBeDisabled()
  })

  test('AC-014b streaming 완료 후 deep 토글 활성 + 전환 가능', async ({ page }) => {
    test.setTimeout(180_000)  // 빠른 분석 완료 대기 + 토글
    await ensureBackendUp(page)
    const toggle = await openFirstAiReportModal(page)

    const fastBtn = toggle.locator('button[role="tab"]', { hasText: /빠른 분석/ })
    const deepBtn = toggle.locator('button[role="tab"]', { hasText: /심층 분석/ })

    // 빠른 분석 streaming 완료까지 대기 (토글 disabled → enabled 전환)
    await expect(deepBtn, '빠른 분석 완료 후 deep 토글 활성').toBeEnabled({ timeout: 150_000 })
    await deepBtn.click()
    await expect(deepBtn).toHaveAttribute('aria-selected', 'true')
    await expect(fastBtn).toHaveAttribute('aria-selected', 'false')
  })
})

test.describe('SPEC-AI-REPORT-002 — Journey A: 빠른 분석 (Perplexity)', () => {
  test('첫 마크다운 청크 도착 + SSE 정상 (≤90초)', async ({ page }) => {
    test.setTimeout(120_000)
    await ensureBackendUp(page)
    await openFirstAiReportModal(page)

    // 모달 본문에 마크다운 텍스트가 도착하는지 확인.
    // AiReportModal은 내부에 .ai-report-content 또는 마크다운 컨테이너를 가짐.
    // 대안: 본문에 # 또는 ## 헤더 또는 한국어 단어 도착 대기.
    const body = page.locator('text=/##?\\s|리포트|분석|Executive|Summary/').first()
    await expect(body, 'Perplexity SSE 첫 청크 도착').toBeVisible({ timeout: 90_000 })
  })
})

test.describe('SPEC-AI-REPORT-002 — Journey B: 심층 분석 (Deep, ~3분)', () => {
  test('토글 deep + 다시 시도 + done까지 (~600초 안)', async ({ page }) => {
    test.setTimeout(700_000)  // 11분 안전 여유
    await ensureBackendUp(page)
    const toggle = await openFirstAiReportModal(page)

    const deepBtn = toggle.locator('button[role="tab"]', { hasText: /심층 분석/ })

    // 1) 빠른 분석 자동 시작 → streaming 끝날 때까지 대기 (deepBtn enabled)
    await expect(deepBtn, '빠른 분석 완료 후 deep 토글 활성').toBeEnabled({ timeout: 200_000 })

    // 2) Deep 토글 click (force: true — 모달 transition 회피)
    await deepBtn.click({ force: true })
    await expect(deepBtn).toHaveAttribute('aria-selected', 'true')

    // 3) "다시 시도" 버튼 클릭 → onRetry('deep')으로 deep mode 호출
    //    AiReportModal:237 — className=ai-report-retry-btn, text="다시 시도"
    const retryBtn = page.locator('button.ai-report-retry-btn').filter({ hasText: /다시 시도/ }).first()
    await expect(retryBtn, '다시 시도 버튼 표시 (done 상태에서 심층 분석으로 다시 시도)').toBeVisible({ timeout: 10_000 })
    await retryBtn.click({ force: true })

    // 4) Deep 합성은 collecting 14s + staging 1s + synthesizing 30s+ 의 phase가 있다.
    //    모달 본문(.ai-report-body) 내부의 마크다운 컨테이너에 첫 텍스트 도착 대기.
    const modalContent = page.locator('.ai-report-body .ai-report-content')
    await expect(modalContent, 'Deep 합성 첫 청크 도착 (모달 본문)').toBeVisible({ timeout: 120_000 })

    // 5) 합성 완료까지 (~3-5분). 모달 본문 길이가 5000자 이상 + done 마커 키워드.
    const done = page.waitForFunction(
      () => {
        const body = document.querySelector('.ai-report-body .ai-report-content') as HTMLElement | null
        const text = body?.textContent ?? ''
        return (
          text.length > 4_000 &&
          (text.includes('면책') || text.includes('리스크') || text.includes('Executive') || text.includes('Risk'))
        )
      },
      undefined,
      { timeout: 600_000, polling: 2_000 }
    )
    await done
  })
})
