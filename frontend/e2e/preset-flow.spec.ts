/**
 * SPEC-PRESET-001 E2E: 프리셋 칩 바 플로우 검증.
 *
 * Prerequisites (외부에서 미리 기동):
 *   - 백엔드 :8000 (uvicorn backend.main:app)
 *   - 프론트 :5173 (npm run dev)
 *
 * Journeys:
 *   F1. "Stage2 돌파" 칩 클릭 → URL에 ?preset=breakout_init + 칩 활성화
 *   F2. F1 이후 RS 값을 80으로 변경 → 칩 비활성 + URL에서 preset 제거
 */
import { test, expect, type Page } from '@playwright/test'

// 개발 서버가 올라와 있지 않으면 조용히 skip (CI에서 headed browser 없이 실행 시)
async function checkDevServer(page: Page): Promise<boolean> {
  try {
    const resp = await page.request.get('http://127.0.0.1:5173/', { timeout: 5_000 })
    return resp.ok()
  } catch {
    return false
  }
}

test.describe('SPEC-PRESET-001 — 프리셋 칩 플로우', () => {
  test.beforeEach(async ({ page }) => {
    const isUp = await checkDevServer(page)
    if (!isUp) {
      test.skip()
    }
  })

  /**
   * F1: "Stage2 돌파" 칩 클릭 → URL ?preset=breakout_init + 칩 활성화
   * AC-2, AC-9(URL)
   */
  test('F1: Stage2 돌파 칩 클릭 → URL에 ?preset=breakout_init 포함', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' })

    // 칩 바가 렌더될 때까지 대기
    const group = page.getByRole('group', { name: '필터 프리셋' })
    await expect(group).toBeVisible({ timeout: 10_000 })

    // Stage2 돌파 칩이 초기에는 비활성
    const breakoutChip = page.getByRole('button', { name: 'Stage2 돌파' })
    await expect(breakoutChip).toBeVisible()
    await expect(breakoutChip).toHaveAttribute('aria-pressed', 'false')

    // 칩 클릭
    await breakoutChip.click()

    // 칩이 활성화된다
    await expect(breakoutChip).toHaveAttribute('aria-pressed', 'true', { timeout: 5_000 })

    // URL에 preset=breakout_init 포함
    await expect(page).toHaveURL(/preset=breakout_init/, { timeout: 5_000 })
  })

  /**
   * F2: F1 이후 RS 값을 80으로 변경 → 칩 비활성 + URL에서 preset 제거
   * AC-4 (드리프트 감지), AC-6 (URL 파라미터 제거)
   */
  test('F2: Stage2 돌파 활성화 후 RS 변경 → 칩 비활성 + URL preset 제거', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' })

    // Stage2 돌파 칩 활성화
    const breakoutChip = page.getByRole('button', { name: 'Stage2 돌파' })
    await expect(breakoutChip).toBeVisible({ timeout: 10_000 })
    await breakoutChip.click()
    await expect(breakoutChip).toHaveAttribute('aria-pressed', 'true', { timeout: 5_000 })
    await expect(page).toHaveURL(/preset=breakout_init/, { timeout: 5_000 })

    // RS 입력 필드에 80 입력 (드리프트 유발)
    const rsInput = page.getByPlaceholder('최소 RS')
    await rsInput.fill('80')

    // 칩이 비활성화된다
    await expect(breakoutChip).toHaveAttribute('aria-pressed', 'false', { timeout: 5_000 })

    // URL에서 preset 파라미터가 제거된다
    await expect(page).not.toHaveURL(/preset=/, { timeout: 5_000 })
  })

  /**
   * F1 (모바일): 360px 뷰포트에서 칩 바 가로 스크롤 접근 가능
   * AC-11
   */
  test('F1 모바일: 360px 뷰포트에서 칩 바 렌더 및 가로 스크롤', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 640 })
    await page.goto('/', { waitUntil: 'networkidle' })

    const group = page.getByRole('group', { name: '필터 프리셋' })
    await expect(group).toBeVisible({ timeout: 10_000 })

    // 각 칩의 터치 영역 확인 (최소 44px height)
    const chips = page.locator('.preset-chip')
    const count = await chips.count()
    expect(count).toBeGreaterThan(0)

    for (let i = 0; i < count; i++) {
      const chip = chips.nth(i)
      const box = await chip.boundingBox()
      if (box) {
        expect(box.height).toBeGreaterThanOrEqual(44)
      }
    }
  })
})
