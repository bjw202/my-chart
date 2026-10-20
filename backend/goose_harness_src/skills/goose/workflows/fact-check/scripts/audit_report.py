#!/usr/bin/env python3
"""Fail-closed delivery checks. Evidence declarations are NOT proof of source truth."""
import argparse, hashlib, json, math, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def digest(raw): return hashlib.sha256(raw).hexdigest()
def stamp(value):
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        return d if d.tzinfo else None
    except (ValueError,TypeError,AttributeError): return None

def audit(data, raw, review=None, preview=None, now=None):
    now=now or datetime.now(timezone.utc); review=review if isinstance(review,dict) else {}
    findings=[]
    def fail(code,owner,message): findings.append({'code':code,'owner':owner,'action':message})
    sources={s.get('id'):s for s in data.get('sources',[]) if isinstance(s,dict)}
    def read_ids(ids, dart=False):
        if not isinstance(ids,list) or not ids:return False
        for sid in ids:
            s=sources.get(sid,{})
            host=(urlsplit(s.get('url') or '').hostname or '').lower()
            if s.get('verification')!='direct_read' or not str(s.get('read_scope','')).strip():return False
            if dart and not (host=='dart.fss.or.kr' or host.endswith('.dart.fss.or.kr')):return False
        return True
    window=data.get('research_window',{})
    cutoff=stamp(window.get('cutoff'))
    historical=window.get('mode')=='historical'
    if not cutoff or cutoff>now or (not historical and cutoff.astimezone(cutoff.tzinfo).date()!=now.astimezone(cutoff.tzinfo).date()):
        fail('FRESHNESS_CUTOFF','goose','실제 실행일·시간대·조사 마감 시각을 확인하고 research_window.cutoff에 기록합니다.')
    if historical and not window.get('user_requested_as_of'):
        fail('HISTORICAL_SCOPE','goose','과거 기준일은 사용자가 지정한 경우에만 적용합니다.')
    if cutoff and not str(data.get('as_of','')).startswith(cutoff.date().isoformat()):
        fail('AS_OF_MISMATCH','goose','표지 기준일과 조사 마감일을 일치시킵니다.')
    searches=window.get('searches',[])
    channels={'original_news'}
    market=str(data.get('company',{}).get('market','')).upper()
    korean=any(x in market for x in ('KRX','KOSPI','KOSDAQ','한국','코스피','코스닥')) or data.get('company',{}).get('country')=='KR'
    deep=data.get('document_type','deep_report')=='deep_report'
    if data.get('document_type','deep_report')=='deep_report':
        channels.update({'company_ir','naver','industry'})
        if korean:channels.add('dart')
    for channel in sorted(channels):
        matching=[]
        for s in searches if isinstance(searches,list) else []:
            at=stamp(s.get('searched_at'))
            if s.get('channel')==channel and at and cutoff and 0<=(cutoff-at).total_seconds()<=86400 and str(s.get('query','')).strip() and str(s.get('note','')).strip():
                if (s.get('result')=='read' and read_ids(s.get('source_ids'))) or s.get('result')=='no_results': matching.append(s)
        if not matching:fail('LATEST_SEARCH_'+channel.upper(),'event-impact' if channel in ('naver','original_news') else 'goose',channel+'의 최근 공시·기사·정정·후속 사건을 검색하고 원문 열람 또는 검색 결과 없음의 근거를 기록합니다. 차단은 완료가 아닙니다.')
    if deep and korean:
        filings=data.get('filing_coverage',{})
        for part in ('body','notes','review_or_audit'):
            r=filings.get(part,{})
            if r.get('status')!='read' or not str(r.get('read_scope','')).strip() or not read_ids(r.get('source_ids'),dart=True):
                fail('DART_'+part.upper(),'earnings-review','DART '+part+' 원문·첨부를 직접 읽고 구간과 문서 출처를 기록합니다. IR 대체 열람만으로 완료 처리하지 않습니다.')
    if cutoff:
        for source in sources.values():
            date_text=str(source.get('published_at',''))[:10]
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}',date_text) and date_text>cutoff.date().isoformat():
                fail('FUTURE_SOURCE','fact-check','조사 기준일 뒤에 발행된 자료를 이번 분석의 근거로 쓰지 않습니다.')
    if deep:
        history=data.get('financial_history',{})
        qrows=history.get('quarters',[]);arows=history.get('annual',[])
        def numeric(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
        valid_q={}
        seen_q=set()
        for r in qrows if isinstance(qrows,list) else []:
            m=re.fullmatch(r'(\d{4})-Q([1-4])',str(r.get('period','')))
            if m and r.get('status') in ('filed','derived') and numeric(r.get('revenue')) and numeric(r.get('operating_profit')) and read_ids(r.get('source_ids'),dart=korean):
                key=int(m[1])*4+int(m[2])
                if key in seen_q:fail('DUPLICATE_QUARTER','earnings-review','중복 분기는 기간을 늘리는 자료로 인정하지 않습니다.')
                seen_q.add(key)
                ended = cutoff and key < cutoff.year*4 + (cutoff.month-1)//3+1
                if not ended:fail('FUTURE_QUARTER','earnings-review','아직 끝나지 않은 분기는 공시 실적에서 제외합니다.')
                else:valid_q[key]=r['period']
        consecutive=sorted(valid_q)
        if len(consecutive)<6 or any(b-a!=1 for a,b in zip(consecutive,consecutive[1:])) or (consecutive and cutoff and cutoff.year*4+(cutoff.month-1)//3+1-consecutive[-1]>3):
            fail('QUARTER_HISTORY','earnings-review','최근 8개 분기를 목표로 최소 6개 연속 공시 분기의 매출·영업이익을 조사합니다. 잠정치는 별도이며 누적 차감 역산은 산식을 보존합니다.')
        valid_a={r.get('year') for r in arows if isinstance(r,dict) and isinstance(r.get('year'),int) and numeric(r.get('revenue')) and numeric(r.get('operating_profit')) and read_ids(r.get('source_ids'))}
        if (valid_a and cutoff and max(valid_a)<cutoff.year-2) or len(valid_a)<3 or (cutoff and any(y>=cutoff.year for y in valid_a)) or any(b-a!=1 for a,b in zip(sorted(valid_a),sorted(valid_a)[1:])):fail('ANNUAL_HISTORY','earnings-review','최근 3개 공시 연도의 실적을 같은 기준으로 비교합니다. 미공개·신규상장은 초안에서 제한과 범위 조정을 설명합니다.')
        charts=[b for s in data.get('sections',[]) for b in s.get('blocks',[]) if b.get('type')=='chart']
        purposes={b.get('purpose') for b in charts}
        for purpose in ('revenue_profit','margins','cashflow'):
            if purpose not in purposes:fail('CHART_'+purpose.upper(),'stock-report',purpose+' 도해를 검증된 실제 수치로 구성합니다. 자료가 없으면 채우지 말고 조사 담당자에게 반환합니다.')
        chart_periods=set()
        for b in charts:
            if b.get('purpose')=='revenue_profit':
                for c in b.get('categories',[]):
                    m=re.search(r'(\d{4})\s*[- /]?\s*Q([1-4])',str(c))
                    if m:chart_periods.add(m[1]+'-Q'+m[2])
        if valid_q and not set(valid_q.values()).issubset(chart_periods):fail('HISTORY_NOT_PRESENTED','stock-report','수집한 분기 원장의 전체 기간을 실적 차트에 반영합니다.')
    checks=('source_accuracy','calculations','coverage','opinion','visual')
    if review.get('input_sha256')!=digest(raw):fail('AUDIT_INPUT_VERSION','fact-check','현재 입력 파일의 해시와 연결된 새 감수 기록을 작성합니다.')
    if not preview or review.get('preview_sha256')!=digest(preview):fail('AUDIT_PREVIEW_VERSION','fact-check','현재 미리보기 HTML을 실제 확인하고 그 파일 해시를 기록합니다.')
    at=stamp(review.get('reviewed_at'))
    if not at or at>now or (cutoff and at<cutoff):fail('AUDIT_TIME','fact-check','조사 완료 후 실제 감수한 시각을 기록합니다.')
    if review.get('mode') not in ('independent_agent','separate_review_pass'):fail('AUDIT_MODE','fact-check','독립 담당자 또는 작성 후 별도 감수 단계의 실제 실행 방식을 기록합니다.')
    for name in checks:
        record=review.get('checks',{}).get(name,{})
        if record.get('status')!='pass' or not str(record.get('evidence','')).strip():fail('REVIEW_'+name.upper(),'fact-check' if name!='visual' else 'stock-report',name+' 감수를 완료하고 실제 관찰·대조 결과를 기록합니다. 선언만으로 통과시키지 않습니다.')
    for issue in review.get('issues',[]):
        if issue.get('status')!='resolved':fail('UNRESOLVED_ISSUE',issue.get('owner','goose'),str(issue.get('description','미해결 결함을 수정합니다.')))
    return {'schema_version':1,'decision':'revise' if findings else 'pass','delivery_allowed':not findings,'input_sha256':digest(raw),'preview_sha256':digest(preview) if preview else None,'checked_at':now.isoformat(),'review':{k:review.get(k) for k in ('reviewed_at','mode','checks','issues')},'findings':findings,'scope':'Local completeness and evidence-record consistency checks plus supplied editorial review. Not proof of factual truth or independent execution.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path);p.add_argument('--review',type=Path);p.add_argument('--preview',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    try:
        raw=a.input.read_bytes();result=audit(json.loads(raw),raw,json.loads(a.review.read_text()) if a.review else None,a.preview.read_bytes() if a.preview else None)
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['delivery_allowed'] else 2
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as e:print('Audit could not complete: '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
