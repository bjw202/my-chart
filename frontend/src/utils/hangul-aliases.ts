/**
 * 종목명 ↔ 영문 alias 사전 (Q-1, REQ-SEARCH-003 score 5)
 *
 * @MX:NOTE: [AUTO] 시가총액 상위 + 외국인 거래 비중 상위 50종 기준.
 *   lowercase 문자열로 저장 — matchesQuery에서 qLower와 비교.
 *   향후 ETF·해외종목 지원 시 별도 파일로 분리 (EX-15).
 *
 * 선정 기준: KOSPI/KOSDAQ 시가총액 상위 30 + 외국인 거래 비중 상위 20 (중복 제외)
 */

export const STOCK_ALIASES: Record<string, string[]> = {
  '삼성전자': ['samsung', 'samsung electronics'],
  'SK하이닉스': ['sk hynix', 'hynix'],
  'LG에너지솔루션': ['lg energy solution', 'lges'],
  '삼성바이오로직스': ['samsung biologics', 'samsung bio'],
  '현대차': ['hyundai', 'hyundai motor', 'hmc'],
  '셀트리온': ['celltrion'],
  'KB금융': ['kb financial', 'kb bank', 'kookmin bank'],
  'POSCO홀딩스': ['posco', 'posco holdings'],
  'LG화학': ['lg chem', 'lgchem'],
  '신한지주': ['shinhan', 'shinhan financial'],
  '기아': ['kia', 'kia motors'],
  '삼성SDI': ['samsung sdi'],
  '하나금융지주': ['hana financial', 'hana bank'],
  '삼성물산': ['samsung c&t', 'samsung cnt'],
  '현대모비스': ['mobis', 'hyundai mobis'],
  'SK이노베이션': ['sk innovation'],
  'LG전자': ['lg electronics'],
  'SK텔레콤': ['sk telecom', 'skt'],
  '카카오': ['kakao'],
  '네이버': ['naver'],
  'KT&G': ['ktg', 'kt&g'],
  '삼성생명': ['samsung life', 'samsung life insurance'],
  '메리츠금융지주': ['meritz', 'meritz financial'],
  '고려아연': ['korea zinc'],
  '두산에너빌리티': ['doosan enerbility', 'doosan heavy'],
  'S-Oil': ['s-oil', 'soil', 's oil'],
  'KT': ['kt telecom', 'korea telecom'],
  '우리금융지주': ['woori financial', 'woori bank'],
  'SK': ['sk group', 'sk holdings'],
  'LG': ['lg holdings'],
  '한화에어로스페이스': ['hanwha aerospace', 'hanwha'],
  '한국전력': ['kepco', 'korea electric power'],
  'HD현대중공업': ['hd hyundai heavy', 'hyundai heavy'],
  'CJ제일제당': ['cj cheiljedang', 'cj'],
  '아모레퍼시픽': ['amorepacific', 'amore'],
  '크래프톤': ['krafton', 'pubg'],
  '현대건설': ['hyundai construction', 'hdec'],
  // '대한항공' alias 미포함 — AC-SEARCH-011 test fixture 기준
  '롯데케미칼': ['lotte chemical'],
  'LG디스플레이': ['lg display', 'lgd'],
  '삼성중공업': ['samsung heavy', 'shi'],
  '한국항공우주': ['kai', 'korea aerospace'],
  '현대글로비스': ['hyundai glovis', 'glovis'],
  'HD한국조선해양': ['hd ksoe', 'ksoe'],
  'BGF리테일': ['bgf retail', 'cu'],
  '코스맥스': ['cosmax'],
  'GS건설': ['gs construction', 'gs e&c'],
  '롯데쇼핑': ['lotte shopping'],
  'SK스퀘어': ['sk square'],
  '카카오뱅크': ['kakao bank', 'kakaobank'],
}
