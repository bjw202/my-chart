#!/usr/bin/env python3
"""Render a source-linked company report with Python 3's standard library only.

No network requests, Markdown evaluation, arbitrary HTML, or external JavaScript.
Validation verifies structure/provenance references, never the truth of research.
"""
import argparse
import base64
import hashlib
import html
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ASSETS = Path(__file__).resolve().parent.parent / "assets"
DECISIONS = ("관심종목 편입", "관망", "편입 보류")
CLAIM_STATES = ("verified", "qualified", "unverified", "inference")
STATE_LABELS = {"verified": "근거", "qualified": "조건부 근거", "unverified": "미확인", "inference": "해석 근거"}
VERIFICATION_LABELS = {"direct_read": "이번 실행 직접 열람", "prior_record": "기존 열람 기록 대조", "blocked": "접근 제한", "not_published": "미공개"}
REPORT_LABELS = {"draft": "초안 · 미검증", "limited": "검토본 · 조사 한계 있음", "verified": "자료 대조 검토본"}
DOCUMENT_TYPES = {"deep_report": "기업 심층 분석", "comparison": "기업 비교 분석", "earnings": "실적 분석", "event": "주요 사건 분석", "portfolio": "포트폴리오 점검", "fact_check": "근거 검증", "briefing": "리서치 브리핑"}
LOCAL_SOURCE_TYPES = {"user_input": "사용자 제공 자료", "local_calculation": "로컬 계산 근거"}
COLORS = ("#902531", "#4f4f4b", "#75615f", "#395d64", "#775c35", "#5c4d71")
ICON_PATHS = (
    '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
    '<path d="M4 3v17h17M7 15l4-5 4 2 5-7"/>',
    '<path d="M4 12h6m0 0 6-7h5m-11 7 6 7h5M18 2l3 3-3 3m0 8 3 3-3 3"/>',
    '<path d="M4 6h14V3H5a2 2 0 0 0-2 2v14h18V7H4M16 11h5v5h-5z"/>',
    '<path d="M12 3v18M5 6h14M8 21h8M5 6l-3 8h6zm14 0-3 8h6z"/>',
    '<path d="M4 3h16v18H4zM8 7h8M8 11h8M8 15h3M8 18h8"/>',
    '<path d="m12 3 8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6zM8 12l3 3 5-6"/>',
    '<path d="M4 12h5m0 0 5-7h6m-11 7h11m-11 0 5 7h6M17 2l3 3-3 3m0 1 3 3-3 3m0 1 3 3-3 3"/>',
    '<path d="m10 14 4-4m-6 6-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m0 2 1-1a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0"/>',
    '<path d="M3 4h18v13H9l-6 4zM7 8h10M7 12h7"/>',
)


class ValidationError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ValidationError(message)


def obj(value, path):
    require(isinstance(value, dict), path + " must be an object")
    return value


def text(value, path):
    require(isinstance(value, str) and bool(value.strip()), path + " must be nonempty text")
    return value


def array(value, path, minimum=1):
    require(isinstance(value, list) and len(value) >= minimum, path + " must be a list with at least " + str(minimum) + " entries")
    return value


def numeric(value, path):
    require(value is None or (isinstance(value, (int, float)) and not isinstance(value, bool)
                             and math.isfinite(value)), path + " must be a finite number or null")


def safe_url(value):
    text(value, "source URL")
    require(not re.search(r"[\s\x00-\x1f\x7f\\]", value), "source URL contains whitespace, controls, or a backslash")
    try:
        parsed = urlsplit(value)
        require(parsed.scheme.lower() in ("https", "http") and bool(parsed.hostname), "source URL must be absolute HTTP(S)")
        require(parsed.username is None and parsed.password is None, "source URL must not contain credentials")
        parsed.port
    except ValueError as exc:
        raise ValidationError("invalid source URL: " + str(exc)) from exc
    return value


def artifact_ref(value):
    """Accept a portable evidence alias, never a local path or executable URL."""
    text(value, "source.artifact_ref")
    require(re.fullmatch(r"[^\W_][\w.-]{0,119}", value) is not None,
            "artifact_ref must be a portable evidence alias, not an absolute/relative path or URL")
    return value


def validate(data):
    obj(data, "report")
    require(data.get("schema_version") == 1 and not isinstance(data.get("schema_version"), bool), "schema_version must be 1")
    document_type = data.get("document_type", "deep_report")
    require(document_type in DOCUMENT_TYPES, "unsupported document_type")
    deep = document_type == "deep_report"
    if deep or "company" in data:
        company = obj(data.get("company"), "company")
        for key in ("name", "ticker", "market"):
            text(company.get(key), "company." + key)
    if "document" in data or "company" not in data:
        document = obj(data.get("document"), "document")
        for key in ("title", "subtitle", "context_label"):
            text(document.get(key), "document." + key)
    if "document" not in data:
        text(data.get("subtitle"), "subtitle")
    text(data.get("as_of"), "as_of")
    require(data.get("status") in REPORT_LABELS, "status must be draft, limited, or verified")
    limits = array(data.get("limitations"), "limitations", 0)
    for value in limits:
        text(value, "limitation")
    if data["status"] == "limited":
        require(bool(limits), "limited report requires limitations")
    sources = {}
    for source in array(data.get("sources"), "sources"):
        obj(source, "source")
        for key in ("id", "title", "publisher", "published_at", "period", "accessed_at", "read_scope", "findings"):
            text(source.get(key), "source." + key)
        sid = source["id"]
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", sid) is not None, "invalid source id")
        require(sid not in sources, "duplicate source id: " + sid)
        if source.get("source_type") in LOCAL_SOURCE_TYPES:
            require("url" in source and source["url"] is None, "local source.url must be explicit null")
            artifact_ref(source.get("artifact_ref"))
        else:
            safe_url(source.get("url"))
        require(source.get("status") in ("read", "unverified"), "source status must be read or unverified")
        require(source.get("verification") in VERIFICATION_LABELS, "source.verification must be direct_read, prior_record, blocked, or not_published")
        if source["verification"] in ("blocked", "not_published"):
            require(source["status"] == "unverified", "blocked/not_published source must be unverified")
        if source["status"] == "unverified":
            text(source.get("attempts"), "unverified source.attempts")
            text(source.get("impact"), "unverified source.impact")
        sources[sid] = source
    claims = []

    def provenance(item, path):
        refs = array(item.get("source_ids"), path + ".source_ids")
        for sid in refs:
            require(isinstance(sid, str) and sid in sources, path + " references unknown source " + str(sid))
        require(len(refs) == len(set(refs)), path + " has duplicate source_ids")
        require(item.get("status") in CLAIM_STATES, path + ".status must be verified, qualified, unverified, or inference")
        if item["status"] == "qualified":
            text(item.get("qualification"), path + ".qualification")
        if item["status"] == "verified":
            require(all(sources[s]["status"] == "read" for s in refs), path + " cannot be verified with unread sources")
        if data["status"] == "verified":
            require(item["status"] != "unverified" and all(sources[s]["status"] == "read" for s in refs), "verified report contains unverified claims or sources")
        claims.append({"path": path, "source_ids": refs, "status": item["status"]})

    def context(item, path):
        for key in ("period", "unit", "basis"):
            text(item.get(key), path + "." + key)

    def paragraph(item, path, opinion=False):
        obj(item, path)
        if opinion:
            sentences = array(item.get("sentences"), path + ".sentences", 5 if deep else 1)
            for sentence in sentences:
                text(sentence, path + ".sentence")
                require(bool(re.search(r"[.!?。！？][\"'’”)]*$", sentence.strip())), path + " sentence must end with punctuation")
        else:
            text(item.get("text"), path + ".text")
        content = ' '.join(item['sentences']) if opinion else item['text']
        highlights = array(item.get('highlights', []), path + '.highlights', 0)
        require(len(highlights) <= 3, path + ' allows at most 3 highlights')
        require(len(set(highlights)) == len(highlights), path + ' duplicate highlights')
        for highlight in highlights:
            text(highlight, path + '.highlight')
            require(highlight in content and len(highlight) <= 100, path + ' highlight must be an exact short substring')
        provenance(item, path)

    for i, kpi in enumerate(array(data.get("kpis", []), "kpis", 0)):
        path = "kpis[" + str(i) + "]"
        obj(kpi, path)
        for key in ("label", "definition"):
            text(kpi.get(key), path + "." + key)
        require("value" in kpi, path + ".value is required; use null when unknown")
        numeric(kpi["value"], path + ".value")
        context(kpi, path)
        provenance(kpi, path)
    for i, item in enumerate(array(data.get("summary", []), "summary", 1 if deep else 0)):
        paragraph(item, "summary[" + str(i) + "]")
    sections = array(data.get("sections"), "sections")
    require(len(sections) == 9 if deep else len(sections) <= 12, "deep_report requires 9 sections; other documents require 1–12")
    chart_count = 0
    for i, section in enumerate(sections):
        path = "sections[" + str(i) + "]"
        obj(section, path)
        text(section.get("title"), path + ".title")
        for j, block in enumerate(array(section.get("blocks"), path + ".blocks")):
            bp = path + ".blocks[" + str(j) + "]"
            obj(block, bp)
            kind = block.get("type")
            require(kind in ("paragraph", "table", "chart", "heading"), bp + " unsupported block type")
            if kind == "heading":
                text(block.get("text"), bp + ".text")
                continue
            if kind == "paragraph":
                paragraph(block, bp)
                continue
            text(block.get("title"), bp + ".title")
            context(block, bp)
            provenance(block, bp)
            if kind == "table":
                headers = array(block.get("headers"), bp + ".headers")
                for header in headers:
                    text(header, bp + ".header")
                for row in array(block.get("rows"), bp + ".rows"):
                    array(row, bp + ".row")
                    require(len(row) == len(headers), bp + " table row length mismatch")
                    for cell in row:
                        require(cell is None or isinstance(cell, (str, int, float)) and not isinstance(cell, bool), bp + " invalid table cell")
                        if not isinstance(cell, str):
                            numeric(cell, bp + ".cell")
            else:
                require(block.get("kind") in ("bar", "line"), bp + " chart kind must be bar or line (no OHLC)")
                cats = array(block.get("categories"), bp + ".categories")
                require(len(cats) <= 40, bp + " maximum 40 categories")
                for cat in cats:
                    text(cat, bp + ".category")
                series = array(block.get("series"), bp + ".series")
                require(len(series) <= len(COLORS), bp + " maximum 6 series")
                for series_item in series:
                    obj(series_item, bp + ".series item")
                    text(series_item.get("label"), bp + ".series.label")
                    values = array(series_item.get("values"), bp + ".series.values")
                    require(len(values) == len(cats), bp + " chart series length mismatch")
                    for value in values:
                        numeric(value, bp + ".series.value")
                chart_count += 1
    paragraphs = []
    if deep or "opinion" in data:
        opinion = obj(data.get("opinion"), "opinion")
        require("decision" in opinion, "opinion.decision is required; use null when evidence is insufficient")
        require(opinion["decision"] is None or opinion["decision"] in DECISIONS, "invalid interest-list decision")
        if opinion["decision"] is None:
            text(opinion.get("decision_reason"), "opinion.decision_reason")
        require(opinion.get("confidence") in ("낮음", "중간", "높음"), "confidence must be 낮음, 중간, or 높음")
        for key in ("lead", "grounds", "conditions"):
            paragraph(opinion.get(key), "opinion." + key)
        paragraphs = array(opinion.get("paragraphs", []), "opinion.paragraphs", 12 if deep else 0)
        require(len(paragraphs) <= 12, "opinion allows at most 12 prose paragraphs")
        for i, item in enumerate(paragraphs):
            paragraph(item, "opinion.paragraphs[" + str(i) + "]", opinion=True)
    if data["status"] == "verified":
        require(all(s["status"] == "read" for s in sources.values()), "verified report contains unread sources")
    return {"schema_version": 1, "structural_validation": "valid", "research_verified_by_renderer": False,
            "note": "Only structure, reference integrity, and numeric representability were checked; source truth, arithmetic, completeness, and investment judgment require independent review.",
            "document_type": document_type, "declared_report_status": data["status"], "claims": claims, "charts": chart_count,
            "opinion_sentence_counts": [len(p["sentences"]) for p in paragraphs],
            "editorial_quality": editorial_quality(data)}


def editorial_quality(data):
    """Review prompts, not an automatic financial or prose quality certification."""
    warnings = []
    paragraphs = data.get('opinion', {}).get('paragraphs', [])
    lengths = [len(' '.join(p['sentences'])) for p in paragraphs]
    if data.get('document_type', 'deep_report') == 'deep_report':
        if paragraphs and all(len(p['sentences']) == 5 for p in paragraphs):
            warnings.append('All 12 paragraphs stop at the minimum 5 sentences; review depth, not only sentence count.')
        if lengths and sum(lengths) / len(lengths) < 400:
            warnings.append('Opinion prose is short relative to the approved detailed-column style; review mechanisms, counterarguments and investor implications. Do not pad.')
        if data.get('opinion', {}).get('decision_scope') != 'research_priority':
            warnings.append('Interest-list research priority must be explicitly separated from valuation and personal allocation.')
        review = data.get('editorial_review', {})
        for criterion in ('argument_depth', 'decision_scope', 'material_coverage', 'visual_review'):
            record = review.get(criterion, {}) if isinstance(review, dict) else {}
            if not isinstance(record, dict) or record.get('status') != 'reviewed' or not isinstance(record.get('evidence'), str) or not record['evidence'].strip():
                warnings.append('Missing evidenced editorial review: ' + criterion)
    return {'warnings': warnings, 'opinion_character_counts': lengths,
            'requires_editorial_review': bool(warnings), 'quality_certified_by_renderer': False}


def esc(value):
    return html.escape(str(value), quote=True)


def fmt(value):
    if value is None:
        return "미확인"
    if isinstance(value, str):
        return value
    if value == 0:
        return "0"
    if abs(value) >= 1e12 or abs(value) < .001:
        return format(value, ".4g")
    return format(value, ",.3f").rstrip("0").rstrip(".")


def refs(item, source_numbers=None):
    status = item["status"]
    label = '<span class="claim-state ' + status + '">' + STATE_LABELS[status] + '</span>'
    links = ' '.join('<a href="#source-' + esc(sid) + '">[' + esc(source_numbers[sid] if source_numbers else sid) + ']</a>' for sid in item["source_ids"])
    qualification = ' · ' + esc(item['qualification']) if status == 'qualified' else ''
    return '<span class="claim-meta">' + label + ' ' + links + qualification + '</span>'


def para(item, opinion=False, source_numbers=None):
    content = ' '.join(item["sentences"]) if opinion else item["text"]
    highlights = item.get('highlights', [])
    if highlights:
        pattern = '(' + '|'.join(re.escape(s) for s in sorted(highlights, key=len, reverse=True)) + ')'
        content = ''.join('<strong class="key-number">' + esc(s) + '</strong>' if s in highlights else esc(s)
                          for s in re.split(pattern, content))
    else:
        content = esc(content)
    return '<p>' + content + ' ' + refs(item, source_numbers) + '</p>'


def icon(index):
    return '<svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON_PATHS[index] + '</svg>'


def chart(block, index, source_numbers=None):
    categories, series = block["categories"], block["series"]
    values = [v for s in series for v in s["values"] if v is not None]
    magnitude = max([abs(v) for v in values] + [1])
    normalized = [v / magnitude for v in values]
    lo, hi = min(normalized + [0]), max(normalized + [0])
    if lo == hi:
        hi = 1
    span = hi - lo
    left, top, bottom, width = 90, 55, 295, max(920, len(categories) * 110 + 120)
    plot_width = width - left - 30
    def y(value):
        return bottom - (value / magnitude - lo) / span * (bottom - top)
    baseline = y(0)
    parts = []
    for tick in range(5):
        normalized_value = lo + span * tick / 4
        coordinate = bottom - tick / 4 * (bottom - top)
        parts.append(f'<line x1="{left}" y1="{coordinate:.2f}" x2="{width-30}" y2="{coordinate:.2f}" stroke="#c8c8c3"/>')
        parts.append(f'<text x="{left-10}" y="{coordinate+6:.2f}" text-anchor="end">{esc(fmt(normalized_value*magnitude))}</text>')
    parts.append(f'<line class="zero-baseline" x1="{left}" y1="{baseline:.2f}" x2="{width-30}" y2="{baseline:.2f}" stroke="#242424"/>')
    step = plot_width / len(categories)
    for ci, category in enumerate(categories):
        center = left + (ci + .5) * step
        parts.append(f'<text x="{center:.2f}" y="333" text-anchor="middle">{esc(category)}</text>')
    for si, s in enumerate(series):
        color = COLORS[si]
        segment = []
        def flush():
            if len(segment) > 1:
                parts.append('<polyline points="' + ' '.join(segment) + '" fill="none" stroke="' + color + '" stroke-width="3"/>')
            segment.clear()
        for ci, value in enumerate(s["values"]):
            center = left + (ci + .5) * step
            if value is None:
                flush()
                continue
            coordinate = y(value)
            tooltip = esc(categories[ci] + ' · ' + s["label"] + ': ' + fmt(value) + ' ' + block["unit"])
            if block["kind"] == "bar":
                bar_width = min(36, step * .72 / len(series))
                x = center - len(series) * bar_width / 2 + si * bar_width
                parts.append(f'<rect x="{x:.2f}" y="{min(coordinate,baseline):.2f}" width="{bar_width*.9:.2f}" height="{abs(coordinate-baseline):.2f}" fill="{color}"><title>{tooltip}</title></rect>')
            else:
                segment.append(f'{center:.2f},{coordinate:.2f}')
                parts.append(f'<circle cx="{center:.2f}" cy="{coordinate:.2f}" r="4" fill="{color}"><title>{tooltip}</title></circle>')
        flush()
    heading_id = "chart-title-" + str(index)
    legend = ''.join('<span><i style="background:' + COLORS[i] + '"></i>' + esc(s["label"]) + '</span>' for i, s in enumerate(series))
    rows = [[cat] + [s["values"][i] for s in series] for i, cat in enumerate(categories)]
    data_table = table_markup(["기간/구분"] + [s["label"] for s in series], rows)
    no_data = '<p class="notice">표시할 수치가 아직 확인되지 않았습니다.</p>' if not values else ''
    return '<figure><figcaption id="' + heading_id + '">' + esc(block["title"]) + '</figcaption><div class="chart-legend">' + legend + '</div>' + no_data + '<div class="chart-scroll"><svg viewBox="0 0 ' + str(width) + ' 355" role="img" aria-labelledby="' + heading_id + '"><desc>음수는 영점 아래에 표시합니다. 미확인 값은 그리지 않으며 정확한 값은 수치 표에 제공합니다.</desc>' + ''.join(parts) + '</svg></div><p class="caption">' + esc(block["period"] + ' · ' + block["basis"] + ' · 단위: ' + block["unit"]) + ' ' + refs(block, source_numbers) + '</p><details><summary>차트 수치 표 보기</summary>' + data_table + '</details></figure>'


def table_markup(headers, rows):
    head = ''.join('<th scope="col">' + esc(h) + '</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(('<th scope="row">' if j == 0 else '<td>') + esc(fmt(cell)) + ('</th>' if j == 0 else '</td>') for j, cell in enumerate(row)) + '</tr>' for row in rows)
    return '<div class="table-wrap"><table><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table></div>'


def render_html(data, artifact_bytes=None, delivery_ready=False):
    validate(data)
    css = (ASSETS / 'report.css').read_text(encoding='utf-8')
    logo = base64.b64encode((ASSETS / 'modu-stock-wordmark.png').read_bytes()).decode('ascii')
    company = data.get('company')
    document = data.get('document')
    document_type = data.get('document_type', 'deep_report')
    title = document['title'] if document else company['name']
    subtitle = document['subtitle'] if document else data['subtitle']
    context_label = document['context_label'] if document else company['market'] + ' / ' + company['ticker']
    source_numbers = {source['id']: i + 1 for i, source in enumerate(data['sources'])}
    masthead = '<header class="masthead"><div class="brand-lockup"><span class="logo-window"><img src="data:image/png;base64,' + logo + '" alt="모두의 주식 — Stock for Everyone" width="2166" height="726"></span><div class="brand-description"><strong>모두의 주식</strong>근거를 읽고, 기업을 해석합니다.</div></div><div class="edition">기준일 ' + esc(data['as_of']) + '<span>' + esc(REPORT_LABELS[data['status']]) + '</span></div></header>'
    kpis = ''.join('<div class="kpi"><span>' + esc(k['label']) + '</span><strong>' + esc(fmt(k['value'])) + '<small>' + esc(k['unit']) + '</small></strong><p class="caption">' + esc(k['period'] + ' · ' + k['basis']) + '<br>' + esc(k['definition']) + ' ' + refs(k, source_numbers) + '</p></div>' for k in data.get('kpis', []))
    audit_banner = '<p class="notice" role="status">' + ('감수 기록 확인 · 최종 보고서' if delivery_ready else '감사 대기 · 최종본 아님 — 조사·내용·화면 검토 후 최종 제출합니다.') + '</p>'
    hero = '<section class="report-hero"><div class="eyebrow">' + esc(DOCUMENT_TYPES[document_type] + ' · ' + context_label) + '</div><h1>' + esc(title) + '</h1><h2>' + esc(subtitle) + '</h2>' + ('<div class="kpis">' + kpis + '</div>' if kpis else '') + '</section>'
    nav = ''.join('<a href="#section-' + str(i+1) + '">' + f'{i+1:02d}. ' + esc(s['title']) + '</a>' for i, s in enumerate(data['sections']))
    opinion_number = len(data['sections']) + 1
    if 'opinion' in data:
        nav += '<a href="#section-' + str(opinion_number) + '">' + f'{opinion_number:02d}. MoAI 오피니언</a>'
    nav += '<a href="#sources">자료 장부</a>'
    content = '<section class="lead-summary"><h3>먼저 읽을 핵심</h3>' + ''.join(para(p, source_numbers=source_numbers) for p in data['summary']) + '</section>' if data.get('summary') else ''
    chart_index = 0
    for i, section in enumerate(data['sections']):
        content += '<section><h2 id="section-' + str(i+1) + '">' + icon(i % 9) + '<span>' + f'{i+1:02d}. ' + esc(section['title']) + '</span></h2>'
        for block in section['blocks']:
            if block['type'] == 'paragraph':
                content += para(block, source_numbers=source_numbers)
            elif block['type'] == 'heading':
                content += '<h3>' + esc(block['text']) + '</h3>'
            elif block['type'] == 'table':
                content += '<h3>' + esc(block['title']) + '</h3>' + table_markup(block['headers'], block['rows']) + '<p class="caption">' + esc(block['period'] + ' · ' + block['basis'] + ' · 단위: ' + block['unit']) + ' ' + refs(block, source_numbers) + '</p>'
            else:
                chart_index += 1
                content += chart(block, chart_index, source_numbers)
        content += '</section>'
    if 'opinion' in data:
        o = data['opinion']
        decision_label = o['decision'] if o['decision'] is not None else '판단 유보 — 근거 부족'
        decision_reason = '<p class="notice">' + esc(o['decision_reason']) + '</p>' if o['decision'] is None else ''
        decision = '<div class="opinion"><div class="opinion-label">🗿 MoAI의 판단 <span>결론 요약 · 확신 수준 ' + esc(o['confidence']) + '</span></div><strong class="opinion-decision">' + esc(decision_label) + '</strong>' + decision_reason + para(o['lead'], source_numbers=source_numbers) + '<div class="opinion-summary"><div><span>핵심 근거</span>' + para(o['grounds'], source_numbers=source_numbers) + '</div><div><span>판단 변경 조건</span>' + para(o['conditions'], source_numbers=source_numbers) + '</div></div><div class="opinion-scale">' + ''.join('<span' + (' class="selected"' if d == o['decision'] else '') + '>' + d + '</span>' for d in DECISIONS) + '</div></div>'
        content += '<section class="moai-column"><h2 id="section-' + str(opinion_number) + '">' + icon(9) + '<span>' + f'{opinion_number:02d}. MoAI 오피니언</span></h2>' + decision + ('<h3 class="column-heading">투자자를 위한 해석</h3>' if o.get('paragraphs') else '') + ''.join(para(p, opinion=True, source_numbers=source_numbers) for p in o.get('paragraphs', [])) + '</section>'
    content += '<section class="limitations"><h3>확인 범위와 남은 한계</h3>' + (''.join('<p>' + esc(x) + '</p>' for x in data['limitations']) if data['limitations'] else '<p>작성자가 별도 한계를 입력하지 않았습니다. 모든 자료를 빠짐없이 확인했다는 뜻은 아닙니다.</p>') + '</section>'
    content += '<section id="sources"><h3>자료 장부</h3><p class="caption">열람·분석 상태는 작성자가 기록한 내용입니다. 재전재와 동일 발행기관의 자료는 독립 출처 수로 중복 계산하지 않습니다.</p><ol class="source-ledger">'
    for s in data['sources']:
        if s.get('source_type') in LOCAL_SOURCE_TYPES:
            source_title = '<strong>' + esc(s['title']) + '</strong><p class="caption">' + esc(LOCAL_SOURCE_TYPES[s['source_type']] + ' · 자료 식별명: ' + artifact_ref(s['artifact_ref'])) + '</p>'
        else:
            source_title = '<a href="' + esc(safe_url(s['url'])) + '" target="_blank" rel="noopener noreferrer">' + esc(s['title']) + '</a>'
        content += '<li id="source-' + esc(s['id']) + '">' + source_title + '<p class="caption">' + esc(s['id'] + ' · ' + s['publisher'] + ' · ' + (VERIFICATION_LABELS[s['verification']] + (' · 미확인 자료' if s['status'] == 'unverified' else ''))) + '<br>발행: ' + esc(s['published_at']) + ' · 대상: ' + esc(s['period']) + ' · 열람: ' + esc(s['accessed_at']) + '</p><p>읽은 구간: ' + esc(s['read_scope']) + '<br>확인 결과: ' + esc(s['findings']) + '</p>'
        if s['status'] == 'unverified':
            content += '<p class="notice">시도한 경로: ' + esc(s['attempts']) + '<br>판단 영향: ' + esc(s['impact']) + '</p>'
        content += '</li>'
    content += '</ol><details><summary>검증 범위 안내</summary><p class="caption">자료 대조 상태는 작성자의 입력 선언입니다. 문서 생성 과정에서는 구조·출처 연결·문장 수를 검사하며 사실의 진실성·계산의 정확성·조사 완전성은 별도 검토 대상입니다.</p></details></section><footer class="actions"><a href="report-input.json" download>입력 원문 JSON</a><a href="source-ledger.json" download>자료 장부 JSON</a><a href="render-validation.json" download>구조 검증 기록</a><span>브라우저의 인쇄 메뉴에서 PDF로 저장할 수 있습니다.</span></footer>'
    if artifact_bytes is None:
        input_bytes = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        validation = validate(data)
        validation['input_sha256'] = hashlib.sha256(input_bytes).hexdigest()
        artifact_bytes = {
            'report-input.json': input_bytes,
            'source-ledger.json': (json.dumps({'as_of': data['as_of'], 'sources': data['sources']}, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
            'render-validation.json': (json.dumps(validation, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
        }
    for filename, payload in artifact_bytes.items():
        href = 'data:application/json;base64,' + base64.b64encode(payload).decode('ascii')
        content = content.replace('href="' + filename + '" download', 'href="' + href + '" download="' + filename + '"')
    rail_note = '관심목록 조사 우선순위에 대한 의견입니다. 거래 실행이나 매수·매도 지시가 아닙니다.' if 'opinion' in data else '자료의 기준일과 범위를 함께 살펴봅니다. 근거 번호를 누르면 자료 장부로 이동합니다.'
    fonts = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&amp;display=swap">'
    return '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(title + ' — 모두의 주식') + '</title>' + fonts + '<style>' + css + '</style></head><body><main>' + masthead + audit_banner + hero + '<div class="reading-layout"><aside class="reading-rail"><div class="rail-inner"><details open><summary>보고서 목차</summary><nav aria-label="보고서 목차">' + nav + '</nav></details><p class="rail-note">' + rail_note + '</p></div></aside><article>' + content + '</article></div></main></body></html>'


def read_input(path):
    raw = Path(path).read_bytes()
    def constant(value):
        raise ValidationError('non-finite JSON constant: ' + value)
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result
    data = json.loads(raw.decode('utf-8'), parse_constant=constant, object_pairs_hook=unique_object)
    return raw, data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--final', action='store_true', help='Require delivery audit before final output')
    parser.add_argument('--audit-review', type=Path)
    parser.add_argument('--preview', type=Path)
    args = parser.parse_args(argv)
    if not args.validate_only and args.output_dir is None:
        parser.error('--output-dir is required unless --validate-only is used')
    if args.final and (args.validate_only or not args.audit_review or not args.preview):
        parser.error('--final requires --audit-review and --preview, and cannot use --validate-only')
    try:
        raw, data = read_input(args.input)
        evidence = validate(data)
        evidence['input_sha256'] = hashlib.sha256(raw).hexdigest()
        evidence['delivery_allowed'] = False
        evidence['delivery_status'] = 'draft_pending_audit'
        if not args.validate_only:
            output = args.output_dir
            names = ('report.html', 'report-input.json', 'source-ledger.json', 'render-validation.json')
            require(args.input.resolve() not in [(output / name).resolve() for name in names], 'input must be outside generated output files; use a separate input filename/directory')
            artifacts = {
                'report-input.json': raw,
                'source-ledger.json': (json.dumps({'as_of': data['as_of'], 'document_type': data.get('document_type', 'deep_report'), **({'company': data['company']} if 'company' in data else {}), **({'document': data['document']} if 'document' in data else {}), 'sources': data['sources']}, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
                'render-validation.json': (json.dumps(evidence, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
            }
            rendered = render_html(data, artifacts)
            if args.final:
                require(not (output / 'report.html').exists(), 'final output already exists; use a new run directory to avoid confusing an old final with this audit')
                import importlib.util
                audit_path = Path(__file__).resolve().parents[2] / 'fact-check/scripts/audit_report.py'
                spec = importlib.util.spec_from_file_location('delivery_audit', audit_path)
                auditor = importlib.util.module_from_spec(spec); spec.loader.exec_module(auditor)
                preview = args.preview.read_bytes()
                require(preview == rendered.encode('utf-8'), 'preview differs from current input/template; regenerate and review the draft')
                review = json.loads(args.audit_review.read_text(encoding='utf-8'))
                receipt = auditor.audit(data, raw, review, preview)
                output.mkdir(parents=True, exist_ok=True)
                (output / 'delivery-audit.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                require(receipt['delivery_allowed'], 'delivery audit requires revision; inspect delivery-audit.json; existing final files are not updated')
                evidence['delivery_allowed'] = True
                evidence['delivery_status'] = 'review_record_passed'
                artifacts['render-validation.json'] = (json.dumps(evidence, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
                rendered = render_html(data, artifacts, delivery_ready=True)
                download = 'data:application/json;base64,' + base64.b64encode((json.dumps(receipt, ensure_ascii=False, indent=2)+'\n').encode()).decode('ascii')
                rendered = rendered.replace('<footer class="actions">', '<footer class="actions"><a href="'+download+'" download="delivery-audit.json">최종 감사 기록</a>')
            output.mkdir(parents=True, exist_ok=True)
            (output / 'report.html').write_text(rendered, encoding='utf-8')
            (output / 'report-input.json').write_bytes(raw)
            (output / 'source-ledger.json').write_text(json.dumps({'as_of': data['as_of'], 'document_type': data.get('document_type', 'deep_report'), **({'company': data['company']} if 'company' in data else {}), **({'document': data['document']} if 'document' in data else {}), 'sources': data['sources']}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            (output / 'render-validation.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'structural_validation': 'valid', 'research_verified_by_renderer': False, 'opinion_sentence_counts': evidence['opinion_sentence_counts'], 'editorial_quality': evidence['editorial_quality'], 'delivery_allowed': evidence['delivery_allowed'], 'output': str(args.output_dir / 'report.html') if not args.validate_only else None}, ensure_ascii=False))
        return 0
    except (ValidationError, OSError, ValueError, TypeError, OverflowError, AttributeError, KeyError) as exc:
        print('Report validation/rendering failed: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
