/**
 * ============================================================================
 * AUTO-BANNER // ENGINE — Centralized Trilingual Locale Loader & Fallback Map
 * Primary source: ./locales/{ko,en,vi}.json (async fetch)
 * Fallback: Embedded offline mirror for local file:// protocol
 * ============================================================================
 */
(function (global) {
  'use strict';

  const SUPPORTED_LANGS = Object.freeze(['ko', 'en', 'vi']);
  const DEFAULT_LANG = 'ko';
  const localeCache = {};

  const EMBEDDED_LOCALES = Object.freeze({
    en: {
  "nav": {
    "overview": "01 // OVERVIEW",
    "xexymix": "02 // XEXYMIX 11",
    "meritz": "03 // MERITZ 3D",
    "telemetry": "04 // QUALITY CHECK",
    "engine": "05 // BRAND SETUP",
    "download": "DOWNLOAD ALL ASSETS"
  },
  "hero": {
    "title_line1": "AUTO-BANNER",
    "title_highlight": "ENGINE",
    "subtitle": "Automated multi-size banner production and high-impact 3D ad creative built for Chai Communication—staying 100% true to brand colors, crisp Korean typography, and ready-to-edit Photoshop files.",
    "command_placeholder": "Chai Communication Campaign Showcase — 13 Ad Deliverables Ready",
    "badge_engine": "CREATIVE AUTOMATION // CAMPAIGN SUITE v1.0",
    "system_status": "STATUS: ALL ASSETS VERIFIED & READY",
    "pill_task1": "TASK 01: 11 AD SIZES",
    "pill_task2": "TASK 02: 2 MASTER PSDs",
    "pill_qa": "15/15 QUALITY CHECKS PASSED",
    "cad_featured": "FEATURED CREATIVE // TASK 02 OPTION 2",
    "cad_title": "Bold 3D Floating Visual",
    "cad_inspect_btn": "ZOOM IN ON 3D '150' FINISH",
    "cad_download_psd": "DOWNLOAD .PSD",
    "cad_safe_zone": "CLEAN TEXT & VISUAL SAFE ZONE // ZERO OVERLAP"
  },
  "hero_hotspots": {
    "pin_aria_prefix": "Explore detail",
    "opt1_tag": "DIRECT RESPONSE // MASTER .PSD",
    "opt1_title": "Option 1 // Classic Direct-Response",
    "opt1_desc": "Clear, trustworthy financial layout with a balanced 2-column split and eye-catching 3D gold coin visuals built to drive clicks.",
    "opt1_cta_download": "DOWNLOAD OPTION 1 .PSD",
    "opt2_tag": "BOLD 3D CONCEPT // MASTER .PSD",
    "opt2_title": "Option 2 // Bold 3D Floating Visual",
    "opt2_desc": "Matte Vermillion '150' 3D centerpiece framed inside a sleek metallic gold geometric cage with 5 floating gold coins.",
    "opt2_cta_download": "DOWNLOAD OPTION 2 .PSD",
    "cta_deep_zoom": "ZOOM IN DETAIL",
    "spec_pin_label": "15/15 QUALITY CHECK",
    "spec_tag": "QUALITY ASSURANCE // 15/15 PASSED",
    "spec_title": "Print-Grade Finish & Clean Photoshop Layers",
    "spec_desc": "Passed all 15 quality checks: natural matte 3D finish with no harsh glare (< 0.5%), zero text overlap, and Korean layer names that open cleanly in Photoshop.",
    "spec_cta_zoom": "ZOOM IN ON 3D '150' FINISH",
    "spec_cta_download": "DOWNLOAD MASTER .PSD"
  },
  "task1_xexymix": {
    "title": "WORKFLOW A // XEXYMIX 11-SIZE BANNER SUITE",
    "badge": "WORKFLOW A // SMART MULTI-SIZE PRODUCTION",
    "description": "Adapting one master design into 11 Korean & global ad placements—with crisp right-angle callouts, completely unobstructed product visuals, and seamless background extensions.",
    "feature_orthogonal": "Clean Right-Angle Callout Lines (Zero Messy Diagonals)",
    "feature_occlusion": "100% Clear Product View (No Text Covering Apparel)",
    "feature_feathering": "Seamless Soft Background Extension for Wide Banners",
    "feature_watermark": "100% Brand-Safe: Zero AI Watermarks",
    "filter_all": "ALL (11)",
    "filter_vertical": "VERTICAL (4)",
    "filter_square": "SQUARE (2)",
    "filter_wide": "WIDE (2)",
    "filter_micro": "COMPACT (3)",
    "toggle_hud": "SHOW / HIDE LAYOUT GUIDES",
    "format_spec": "FORMAT: WEB-READY sRGB JPEG (HIGH QUALITY // UNDER 800KB)",
    "source_master": "ORIGINAL MASTER FILE"
  },
  "keepsake": {
    "folder_title": "11-Size Ad Banner Collection",
    "folder_hint_open": "[ CLICK TO VIEW ALL 11 SIZES ]",
    "folder_hint_close": "[ CLOSE COLLECTION ]",
    "flip_hint": "HOVER ANY CARD TO VIEW AD SPECS",
    "items_count_suffix": "SIZES",
    "label_resolution": "DIMENSIONS",
    "label_ratio": "ASPECT RATIO",
    "label_weight": "FILE SIZE",
    "label_stepping": "CLEAN GUIDES",
    "label_watermark": "AI WATERMARK",
    "status_passed": "PASSED",
    "watermark_compliant": "NONE (CLEAN)",
    "footer_verified": "READY",
    "btn_download_zip": "DOWNLOAD ALL 11 SIZES (.ZIP)"
  },
  "task2_meritz": {
    "title": "WORKFLOW B // MERITZ CREATIVE CONCEPTS",
    "badge": "WORKFLOW B // HIGH-IMPACT AD CREATIVE",
    "description": "Compare Option 1 (Classic Direct-Response) and Option 2 (Bold 3D Floating Visual) side by side—both delivered with fully organized, editable Photoshop (.PSD) masters.",
    "opt1_title": "OPTION 1 // CLASSIC DIRECT-RESPONSE",
    "opt1_desc": "Clean, trustworthy 2-column financial ad layout paired with a gleaming 3D gold coin highlight that directs attention straight to the offer.",
    "opt1_eyebrow": "OPTION 01 // CONVERSION FOCUSED",
    "opt1_chip": "7 ORGANIZED PSD GROUPS",
    "opt2_title": "OPTION 2 // BOLD 3D FLOATING VISUAL",
    "opt2_desc": "Dynamic hero-angle perspective featuring a matte Vermillion Red '150' 3D centerpiece inside a metallic gold geometric frame, surrounded by 5 floating coins with soft cinematic blur.",
    "opt2_eyebrow": "OPTION 02 // STANDOUT 3D CONCEPT",
    "opt2_chip": "3D CENTERPIECE + GOLD FRAME",
    "brand_purity_title": "OFFICIAL MERITZ BRAND PALETTE",
    "brand_purity_desc": "Click any official Meritz brand color swatch to copy its HEX code",
    "brand_purity_badge": "100% ON-BRAND COLORS",
    "zoom_instruction": "CLICK TO ZOOM IN ON 3D FINISH",
    "btn_preview_jpg": "DOWNLOAD PREVIEW .JPG",
    "modal_title": "CLOSE-UP 3D DETAIL VIEWER",
    "modal_eyebrow": "CLOSE-UP VIEW // 3D '150' CENTERPIECE",
    "modal_heading": "Matte Finish & Geometric Gold Frame",
    "modal_desc": "Move your cursor across the banner to inspect the natural matte finish on the Meritz Red (#EF3B24) '150' sculpture, crisp gold frame lines, and balanced Korean typography.",
    "modal_toggle_zoom": "SWITCH 2.35x / 1.0x ZOOM",
    "modal_download_psd": "DOWNLOAD LAYERED .PSD"
  },
  "under_the_hood": {
    "title": "QUALITY ASSURANCE // 15-POINT CHECKLIST",
    "badge": "PRODUCTION WORKFLOW // AUTOMATED QUALITY CHECK",
    "description": "Every banner goes through a 3-stage studio workflow and 15 automated quality checks—ensuring clean Photoshop layers, readable Korean copy, and web-ready file sizes before delivery.",
    "pipeline_title": "3-STAGE STUDIO PRODUCTION WORKFLOW",
    "pipeline_desc": "END-TO-END CREATIVE PRODUCTION // VERIFIED OUTPUT",
    "role_art": "Step 01 — Creative Asset & 3D Art Production",
    "role_art_desc": "Unpacks the original master PSD cleanly, crafts the matte-finish 3D '150' centerpiece and metallic gold frame, and preserves crisp product cutouts.",
    "role_compositor": "Step 02 — Smart Multi-Size Layout & Photoshop Export",
    "role_compositor_desc": "Adapts layouts cleanly across all 11 ad dimensions with right-angle callout lines, smooth wide-banner backgrounds, and organized PSD files with clean Korean layer names.",
    "role_qa": "Step 03 — 15-Point Automated Quality Check",
    "role_qa_desc": "Verifies every deliverable before handoff: natural matte 3D finish (< 0.5% harsh glare), zero Korean text overlap, true sRGB web color, and file weights under 800KB.",
    "telemetry_title": "QUALITY ASSURANCE SCORECARD (LIVE SUMMARY)",
    "rules_passed": "15/15 QUALITY CHECKS PASSED",
    "rule_kerning": "Korean Typography Spacing & Readability",
    "rule_collision": "Zero Overlap Between Text & Visuals",
    "rule_anti_plastic": "Natural Matte 3D Surface (No Plastic Glare)",
    "rule_luni": "Clean Korean Layer Names in Photoshop (.PSD)",
    "rule_layers": "XEXYMIX 11-Size Clean Layout Alignment",
    "rule_weight": "Fast-Loading Size (<= 800KB) & Zero AI Watermarks",
    "col_rule_id": "CHECK ID",
    "col_gate": "QUALITY STANDARD",
    "col_constraint": "TARGET",
    "col_measured": "RESULT",
    "col_status": "STATUS"
  },
  "manifest_engine": {
    "title": "MULTI-BRAND READY // REUSABLE CAMPAIGN SYSTEM",
    "badge": "CENTRAL CAMPAIGN CONFIG // BRAND-READY",
    "description": "All campaign assets, brand colors, and ad sizes are managed in one clean configuration file—making it effortless to spin up a new campaign for any brand in minutes.",
    "white_label_desc": "ACTIVE CAMPAIGN: CHAI COMMUNICATION",
    "white_label_active": "PREVIEWING SAMPLE BRAND: SAMSUNG CAMPAIGN",
    "btn_toggle_demo": "PREVIEW ANOTHER BRAND (SAMSUNG DEMO)",
    "btn_restore_demo": "RESTORE CHAI COMMUNICATION CAMPAIGN",
    "btn_copy_json": "COPY CAMPAIGN CONFIG",
    "btn_copied_json": "COPIED TO CLIPBOARD"
  },
  "footer": {
    "download_title": "DOWNLOAD CENTER // CHAI COMMUNICATION DELIVERABLES",
    "download_desc": "Complete Verified Delivery Package — Task 1 (11 Web-Ready sRGB JPEGs under 800KB) & Task 2 (2 Layered Master PSDs + Previews)",
    "task1_download_label": "TASK 01 // XEXYMIX 11-SIZE PACKAGE",
    "task1_card_desc": "11 web-ready sRGB JPEG banners exported from the master PSD. Every placement under 800KB with zero AI watermarks.",
    "task2_download_label": "TASK 02 // MERITZ CREATIVE PACKAGE",
    "repo_label": "DOWNLOAD CAMPAIGN CONFIG (.JSON)",
    "browse_all_11": "VIEW ALL 11 AD SIZES"
  },
  "assembly": {
    "status_init": "⚙️ INITIALIZING BLUEPRINT FRAME...",
    "status_injecting": "⚙️ COMPOSING PRODUCT & COPY MODULES...",
    "status_assembling": "⚙️ LIVE ASSEMBLING MODULES...",
    "status_aligned": "✓ PERFECTLY ALIGNED",
    "btn_live_preview": "LAUNCH LIVE 11-RATIO ASSEMBLY",
    "btn_replay": "▶ REPLAY ASSEMBLY",
    "modal_ratio_title": "LIVE PARAMETRIC ASSEMBLY // XEXYMIX 11 RATIOS"
  }
},
    ko: {
  "nav": {
    "overview": "01 // 개요",
    "xexymix": "02 // 젝시믹스 11종",
    "meritz": "03 // 메리츠 3D",
    "telemetry": "04 // 품질 검수",
    "engine": "05 // 브랜드 설정",
    "download": "전체 소재 다운로드"
  },
  "hero": {
    "title_line1": "AUTO-BANNER",
    "title_highlight": "ENGINE",
    "subtitle": "차이커뮤니케이션 과제를 위해 구축된 다규격 배너 자동 제작 및 하이임팩트 3D 크리에이티브 쇼케이스. 브랜드 컬러 준수, 깔끔한 한글 타이포그래피, 즉시 편집 가능한 레이어드 PSD까지 한 번에 완성합니다.",
    "command_placeholder": "차이커뮤니케이션 캠페인 쇼케이스 — 총 13종 광고 소재 납품 준비 완료",
    "badge_engine": "크리에이티브 자동화 // 캠페인 스위트 v1.0",
    "system_status": "상태: 전 소재 검수 완료 · 즉시 집행 가능",
    "pill_task1": "과제 01: 11종 매체 규격",
    "pill_task2": "과제 02: 마스터 PSD 2종",
    "pill_qa": "15/15 품질 검수 전 항목 통과",
    "cad_featured": "대표 크리에이티브 // 과제 02 2안",
    "cad_title": "입체 3D 플로팅 혁신형",
    "cad_inspect_btn": "3D '150' 매트 질감 자세히 보기",
    "cad_download_psd": "원본 .PSD 다운로드",
    "cad_safe_zone": "텍스트 · 비주얼 안전 영역 준수 // 겹침 0%"
  },
  "hero_hotspots": {
    "pin_aria_prefix": "상세 정보 보기",
    "opt1_tag": "전환 집중형 // 마스터 .PSD",
    "opt1_title": "1안 // 혜택 집중 정통 퍼포먼스형",
    "opt1_desc": "신뢰감 있는 2단 분할 금융 레이아웃과 시선을 사로잡는 메탈릭 3D 골드 코인으로 즉각적인 클릭 전환을 유도하는 정통 퍼포먼스 배너입니다.",
    "opt1_cta_download": "1안 원본 .PSD 다운로드",
    "opt2_tag": "하이임팩트 3D // 마스터 .PSD",
    "opt2_title": "2안 // 입체 3D 플로팅 혁신형",
    "opt2_desc": "매트 버밀리온 '150' 3D 오브제를 세련된 골드 기하학 프레임과 5개의 플로팅 골드 코인으로 감싸 강렬한 주목도를 완성했습니다.",
    "opt2_cta_download": "2안 원본 .PSD 다운로드",
    "cta_deep_zoom": "디테일 확대 보기",
    "spec_pin_label": "15/15 품질 검수 완료",
    "spec_tag": "품질 검수 완료 // 15/15 통과",
    "spec_title": "완벽한 마감 품질 & 정리된 포토샵 레이어",
    "spec_desc": "과도한 광택 없는 자연스러운 매트 3D 질감(< 0.5%), 한글 텍스트 겹침 0px, 포토샵에서 깨짐 없이 열리는 한글 레이어명까지 15가지 품질 검수를 모두 통과했습니다.",
    "spec_cta_zoom": "3D '150' 매트 질감 자세히 보기",
    "spec_cta_download": "마스터 .PSD 다운로드"
  },
  "task1_xexymix": {
    "title": "워크플로우 A // 젝시믹스 11종 배너 패키지",
    "badge": "워크플로우 A // 스마트 다규격 리사이징",
    "description": "하나의 마스터 디자인을 국내외 11개 광고 매체 규격으로 정교하게 확장했습니다. 깔끔한 직각 가이드, 제품을 가리지 않는 여백 설계, 이음매 없는 자연스러운 배경 마감을 확인하세요.",
    "feature_orthogonal": "깔끔한 직각 콜아웃 가이드 (사선 왜곡 없음)",
    "feature_occlusion": "제품 실루엣 100% 보호 (텍스트·요소 가림 없음)",
    "feature_feathering": "가로형 배너를 위한 이음매 없는 자연스러운 배경 확장",
    "feature_watermark": "브랜드 정책 100% 준수: AI 워터마크 제로",
    "filter_all": "전체 (11)",
    "filter_vertical": "세로형 (4)",
    "filter_square": "정방형 (2)",
    "filter_wide": "가로형 (2)",
    "filter_micro": "소형 (3)",
    "toggle_hud": "레이아웃 가이드 보기 / 숨기기",
    "format_spec": "포맷: 웹 최적화 sRGB JPEG (고화질 // 800KB 이하)",
    "source_master": "원본 마스터 파일"
  },
  "keepsake": {
    "folder_title": "11종 광고 배너 컬렉션",
    "folder_hint_open": "[ 클릭하여 11종 배너 펼치기 ]",
    "folder_hint_close": "[ 컬렉션 접기 ]",
    "flip_hint": "카드에 마우스를 올려 매체 규격 확인",
    "items_count_suffix": "종 규격",
    "label_resolution": "해상도",
    "label_ratio": "화면 비율",
    "label_weight": "파일 용량",
    "label_stepping": "직각 가이드",
    "label_watermark": "AI 워터마크",
    "status_passed": "통과",
    "watermark_compliant": "없음 (정상)",
    "footer_verified": "검수 완료",
    "btn_download_zip": "11종 전체 배너 다운로드 (.ZIP)"
  },
  "task2_meritz": {
    "title": "워크플로우 B // 메리츠 크리에이티브 시안",
    "badge": "워크플로우 B // 하이임팩트 광고 제작",
    "description": "1안(혜택 집중 정통 퍼포먼스형)과 2안(입체 3D 플로팅 혁신형)을 나란히 비교해 보세요. 두 시안 모두 즉시 수정 가능한 레이어드 마스터 PSD 원본을 제공합니다.",
    "opt1_title": "1안 // 혜택 집중 정통 퍼포먼스형",
    "opt1_desc": "직관적인 2단 분할 금융 레이아웃과 메탈릭 3D 골드 코인 포인트로 핵심 혜택에 시선을 집중시키는 정통 퍼포먼스 시안입니다.",
    "opt1_eyebrow": "1안 // 전환 최적화 시안",
    "opt1_chip": "7개 그룹 정리 PSD",
    "opt2_title": "2안 // 입체 3D 플로팅 혁신형",
    "opt2_desc": "로우앵글 원근감의 매트 버밀리온 레드 '150' 3D 오브제, 골드 기하학 프레임, 시네마틱 심도 블러가 더해진 5개의 플로팅 코인으로 시선을 압도합니다.",
    "opt2_eyebrow": "2안 // 하이컨셉 3D 시안",
    "opt2_chip": "3D 오브제 + 골드 프레임",
    "brand_purity_title": "메리츠 공식 브랜드 컬러 팔레트",
    "brand_purity_desc": "메리츠 공식 브랜드 컬러를 클릭하면 HEX 코드가 복사됩니다",
    "brand_purity_badge": "브랜드 컬러 100% 준수",
    "zoom_instruction": "클릭하여 3D 질감 확대 보기",
    "btn_preview_jpg": "미리보기 .JPG 다운로드",
    "modal_title": "3D 디테일 확대 뷰어",
    "modal_eyebrow": "클로즈업 // 3D '150' 오브제",
    "modal_heading": "매트 질감 & 골드 기하학 프레임",
    "modal_desc": "커서를 움직여 메리츠 레드(#EF3B24) '150' 오브제의 고급스러운 매트 질감, 정교한 골드 프레임 라인, 균형 잡힌 한글 타이포그래피를 가까이서 확인하세요.",
    "modal_toggle_zoom": "2.35배 / 1.0배 확대 전환",
    "modal_download_psd": "레이어드 .PSD 다운로드"
  },
  "under_the_hood": {
    "title": "품질 보증 // 15단계 검수 체크리스트",
    "badge": "제작 프로세스 // 자동 품질 검증",
    "description": "모든 배너는 3단계 전문 제작 공정과 15가지 자동 품질 검수를 거쳐 깔끔한 포토샵 레이어, 완벽한 한글 가독성, 매체 최적화 용량으로 납품됩니다.",
    "pipeline_title": "3단계 자동화 제작 프로세스",
    "pipeline_desc": "엔드투엔드 크리에이티브 제작 // 일관된 고품질 납품",
    "role_art": "1단계 — 비주얼 에셋 추출 및 3D 아트 제작",
    "role_art_desc": "원본 마스터 PSD에서 에셋을 깔끔하게 분리하고, 매트 질감의 3D '150' 오브제와 골드 프레임, 정교한 제품 누끼를 제작합니다.",
    "role_compositor": "2단계 — 11종 스마트 레이아웃 배치 및 PSD 패키징",
    "role_compositor_desc": "11개 매체 규격에 맞춰 직각 가이드와 자연스러운 배경 확장을 적용하고, 포토샵에서 바로 편집할 수 있는 한글 레이어 구조의 PSD를 완성합니다.",
    "role_qa": "3단계 — 15개 항목 자동 품질 검수",
    "role_qa_desc": "납품 전 모든 소재의 매트 질감(< 0.5% 과광택 방지), 한글 텍스트 겹침 0px, 웹 표준 sRGB 컬러 및 800KB 이하 용량 규격을 빠짐없이 검증합니다.",
    "telemetry_title": "품질 검수 성적표 (실시간 연동)",
    "rules_passed": "15/15 품질 검수 전 항목 통과",
    "rule_kerning": "한글 타이포그래피 자간 및 가독성",
    "rule_collision": "텍스트 · 이미지 겹침 제로 검증",
    "rule_anti_plastic": "3D 오브제 자연스러운 매트 질감 유지",
    "rule_luni": "포토샵(.PSD) 한글 레이어명 호환성",
    "rule_layers": "젝시믹스 11종 매체 규격 정렬 검증",
    "rule_weight": "경량 파일 용량(800KB 이하) 및 AI 워터마크 제로",
    "col_rule_id": "항목 ID",
    "col_gate": "검수 항목",
    "col_constraint": "기준치",
    "col_measured": "측정 결과",
    "col_status": "상태"
  },
  "manifest_engine": {
    "title": "멀티 브랜드 확장 // 재사용 가능한 캠페인 시스템",
    "badge": "통합 캠페인 설정 // 브랜드 즉시 전환",
    "description": "모든 캠페인 소재, 브랜드 컬러, 매체 규격을 하나의 설정 파일로 통합 관리하여 어떤 브랜드의 신규 캠페인에도 몇 분 만에 즉시 적용할 수 있습니다.",
    "white_label_desc": "현재 적용 캠페인: 차이커뮤니케이션",
    "white_label_active": "샘플 브랜드 미리보기 활성: 삼성 캠페인",
    "btn_toggle_demo": "타 브랜드 적용 미리보기 (삼성 데모)",
    "btn_restore_demo": "차이커뮤니케이션 캠페인으로 복원",
    "btn_copy_json": "캠페인 설정 복사",
    "btn_copied_json": "클립보드에 복사 완료"
  },
  "footer": {
    "download_title": "다운로드 센터 // 차이커뮤니케이션 과제 성과물",
    "download_desc": "검수 완료된 전체 납품 패키지 — 과제 1 (800KB 이하 웹 최적화 sRGB JPEG 11종) 및 과제 2 (레이어드 마스터 PSD 2종 + 미리보기)",
    "task1_download_label": "과제 01 // 젝시믹스 11종 패키지",
    "task1_card_desc": "원본 마스터 PSD에서 제작된 11종 sRGB JPEG 배너. 전 규격 800KB 이하 및 AI 워터마크 제로 기준을 준수했습니다.",
    "task2_download_label": "과제 02 // 메리츠 크리에이티브 패키지",
    "repo_label": "캠페인 설정 파일 다운로드 (.JSON)",
    "browse_all_11": "11종 전체 배너 보기"
  },
  "assembly": {
    "status_init": "⚙️ 블루프린트 프레임 초기화 중...",
    "status_injecting": "⚙️ 상품 · 카피 모듈 데이터 배치 중...",
    "status_assembling": "⚙️ 실시간 모듈 조합 중...",
    "status_aligned": "✓ 규격 정렬 완료",
    "btn_live_preview": "11종 실시간 모듈 조합 미리보기",
    "btn_replay": "▶ 레이어 조립 다시보기",
    "modal_ratio_title": "실시간 파라메트릭 조합 // 젝시믹스 11종"
  }
},
    vi: {
  "nav": {
    "overview": "01 // TỔNG QUAN",
    "xexymix": "02 // XEXYMIX 11",
    "meritz": "03 // MERITZ 3D",
    "telemetry": "04 // KIỂM DUYỆT",
    "engine": "05 // CẤU HÌNH",
    "download": "TẢI TRỌN BỘ ẤN PHẨM"
  },
  "hero": {
    "title_line1": "AUTO-BANNER",
    "title_highlight": "ENGINE",
    "subtitle": "Giải pháp tự động sản xuất banner đa kích thước và thiết kế sáng tạo 3D cho chiến dịch Chai Communication—chuẩn xác từng mã màu thương hiệu, chữ rõ nét không chồng chéo và bàn giao file Photoshop phân lớp sẵn sàng chỉnh sửa.",
    "command_placeholder": "Bộ Ấn Phẩm Chiến Dịch Chai Communication — 13 Thành Phẩm Sẵn Sàng",
    "badge_engine": "TỰ ĐỘNG HÓA SÁNG TẠO // BỘ ẤN PHẨM v1.0",
    "system_status": "TRẠNG THÁI: ĐÃ KIỂM DUYỆT & SẴN SÀNG",
    "pill_task1": "BÀI 01: 11 KÍCH THƯỚC",
    "pill_task2": "BÀI 02: 2 FILE PSD GỐC",
    "pill_qa": "15/15 TIÊU CHUẨN CHẤT LƯỢNG ĐẠT",
    "cad_featured": "THIẾT KẾ TIÊU BIỂU // BÀI 02 PHƯƠNG ÁN 2",
    "cad_title": "Điểm Nhấn 3D Nổi Bật",
    "cad_inspect_btn": "PHÓNG TO CHI TIẾT 3D '150'",
    "cad_download_psd": "TẢI FILE .PSD",
    "cad_safe_zone": "VÙNG AN TOÀN CHỮ & HÌNH ẢNH // KHÔNG CHỒNG CHÉO"
  },
  "hero_hotspots": {
    "pin_aria_prefix": "Xem chi tiết",
    "opt1_tag": "CHUYỂN ĐỔI TRỰC TIẾP // FILE .PSD GỐC",
    "opt1_title": "Phương Án 1 // Bố Cục Tài Chính Chuẩn Mực",
    "opt1_desc": "Bố cục quảng cáo tài chính rõ ràng, đáng tin cậy với cấu trúc 2 cột cân đối cùng điểm nhấn đồng xu vàng 3D thu hút lượt nhấp.",
    "opt1_cta_download": "TẢI .PSD PHƯƠNG ÁN 1",
    "opt2_tag": "Ý TƯỞNG 3D ĐỘT PHÁ // FILE .PSD GỐC",
    "opt2_title": "Phương Án 2 // Điểm Nhấn 3D Nổi Bật",
    "opt2_desc": "Con số 3D '150' đỏ nhám sang trọng đặt trong khung đa giác ánh kim cùng 5 đồng xu vàng lơ lửng tạo chiều sâu hút mắt.",
    "opt2_cta_download": "TẢI .PSD PHƯƠNG ÁN 2",
    "cta_deep_zoom": "PHÓNG TO CHI TIẾT",
    "spec_pin_label": "15/15 ĐẠT CHUẨN CHẤT LƯỢNG",
    "spec_tag": "KIỂM DUYỆT CHẤT LƯỢNG // 15/15 ĐẠT CHUẨN",
    "spec_title": "Hoàn Thiện Sắc Nét & Layer Photoshop Gọn Gàng",
    "spec_desc": "Vượt qua toàn bộ 15 tiêu chuẩn kiểm duyệt: bề mặt 3D nhám lì tự nhiên không lóa nhựa (< 0.5%), chữ Hàn Quốc thoáng rõ không chồng chéo và tên layer tiếng Hàn hiển thị chuẩn trong Photoshop.",
    "spec_cta_zoom": "PHÓNG TO CHI TIẾT 3D '150'",
    "spec_cta_download": "TẢI FILE .PSD GỐC"
  },
  "task1_xexymix": {
    "title": "QUY TRÌNH A // BỘ BANNER XEXYMIX 11 KÍCH THƯỚC",
    "badge": "QUY TRÌNH A // SẢN XUẤT ĐA KÍCH THƯỚC THÔNG MINH",
    "description": "Chuyển đổi một thiết kế gốc thành trọn bộ 11 kích thước quảng cáo Hàn Quốc & toàn cầu—đường dẫn chú thích vuông góc sắc nét, sản phẩm luôn hiển thị trọn vẹn và nền banner ngang nối mượt tự nhiên.",
    "feature_orthogonal": "Đường dẫn chú thích vuông góc sắc nét (Không lệch chéo)",
    "feature_occlusion": "Giữ trọn hình ảnh sản phẩm (Không chữ hay khung che lấp)",
    "feature_feathering": "Mở rộng phông nền mềm mượt cho banner ngang không vết nối",
    "feature_watermark": "An toàn thương hiệu 100%: Không dính Watermark AI",
    "filter_all": "TẤT CẢ (11)",
    "filter_vertical": "DỌC (4)",
    "filter_square": "VUÔNG (2)",
    "filter_wide": "NGANG (2)",
    "filter_micro": "NHỎ GỌN (3)",
    "toggle_hud": "BẬT / TẮT LƯỚI BỐ CỤC",
    "format_spec": "ĐỊNH DẠNG: ẢNH sRGB JPEG CHUẨN WEB (SẮC NÉT // DƯỚI 800KB)",
    "source_master": "FILE THIẾT KẾ GỐC"
  },
  "keepsake": {
    "folder_title": "Bộ Sưu Tập 11 Kích Thước Banner",
    "folder_hint_open": "[ NHẤN ĐỂ XEM ĐỦ 11 KÍCH THƯỚC ]",
    "folder_hint_close": "[ THU GỌN BỘ SƯU TẬP ]",
    "flip_hint": "RÊ CHUỘT VÀO THẺ ĐỂ XEM THÔNG SỐ BANNER",
    "items_count_suffix": "KÍCH THƯỚC",
    "label_resolution": "KÍCH THƯỚC",
    "label_ratio": "TỶ LỆ KHUNG",
    "label_weight": "DUNG LƯỢNG",
    "label_stepping": "ĐƯỜNG DẪN GỌN",
    "label_watermark": "WATERMARK AI",
    "status_passed": "ĐẠT CHUẨN",
    "watermark_compliant": "KHÔNG CÓ (SẠCH)",
    "footer_verified": "SẴN SÀNG",
    "btn_download_zip": "TẢI TRỌN BỘ 11 KÍCH THƯỚC (.ZIP)"
  },
  "task2_meritz": {
    "title": "QUY TRÌNH B // PHƯƠNG ÁN SÁNG TẠO MERITZ",
    "badge": "QUY TRÌNH B // THIẾT KẾ SÁNG TẠO ẤN TƯỢNG",
    "description": "So sánh trực tiếp giữa Phương Án 1 (Bố Cục Tài Chính Chuẩn Mực) và Phương Án 2 (Điểm Nhấn 3D Nổi Bật)—cả hai đều đi kèm file Photoshop (.PSD) phân lớp rõ ràng để chỉnh sửa tức thì.",
    "opt1_title": "PHƯƠNG ÁN 1 // BỐ CỤC TÀI CHÍNH CHUẨN MỰC",
    "opt1_desc": "Bố cục quảng cáo tài chính 2 cột rõ ràng, dễ đọc, kết hợp đồng xu vàng 3D ánh kim dẫn mắt trực tiếp vào ưu đãi chính.",
    "opt1_eyebrow": "PHƯƠNG ÁN 01 // TỐI ƯU CHUYỂN ĐỔI",
    "opt1_chip": "7 NHÓM LAYER GỌN GÀNG",
    "opt2_title": "PHƯƠNG ÁN 2 // ĐIỂM NHẤN 3D NỔI BẬT",
    "opt2_desc": "Góc nhìn 3D ấn tượng với khối số '150' đỏ nhám sang trọng bên trong khung đa giác ánh kim, kết hợp 5 đồng xu vàng lơ lửng và hiệu ứng xóa phông điện ảnh.",
    "opt2_eyebrow": "PHƯƠNG ÁN 02 // Ý TƯỞNG 3D ẤN TƯỢNG",
    "opt2_chip": "KHỐI 3D + KHUNG ÁNH KIM",
    "brand_purity_title": "BẢNG MÀU CHUẨN THƯƠNG HIỆU MERITZ",
    "brand_purity_desc": "Nhấn vào bất kỳ màu chính thức nào của Meritz để sao chép mã HEX",
    "brand_purity_badge": "CHUẨN 100% MÀU THƯƠNG HIỆU",
    "zoom_instruction": "NHẤN ĐỂ PHÓNG TO CHI TIẾT 3D",
    "btn_preview_jpg": "TẢI ẢNH XEM TRƯỚC .JPG",
    "modal_title": "KÍNH LÚP XEM CHI TIẾT BỀ MẶT 3D",
    "modal_eyebrow": "XEM CẬN CẢNH // KHỐI 3D '150'",
    "modal_heading": "Bề Mặt Nhám Lì & Khung Đa Giác Ánh Kim",
    "modal_desc": "Di chuyển chuột trên hình để quan sát chất liệu nhám lì tự nhiên trên khối số '150' đỏ Meritz (#EF3B24), đường nét khung ánh kim sắc sảo và khoảng cách chữ Hàn Quốc cân đối.",
    "modal_toggle_zoom": "ĐỔI MỨC PHÓNG TO 2.35x / 1.0x",
    "modal_download_psd": "TẢI FILE .PSD PHÂN LỚP"
  },
  "under_the_hood": {
    "title": "QUY TRÌNH SẢN XUẤT // 15 TIÊU CHUẨN CHẤT LƯỢNG",
    "badge": "QUY TRÌNH BÀN GIAO // KIỂM DUYỆT TỰ ĐỘNG",
    "description": "Mỗi banner đều trải qua quy trình sản xuất 3 bước và 15 tiêu chuẩn kiểm duyệt tự động—đảm bảo file Photoshop sạch đẹp, chữ Hàn Quốc rõ ràng và dung lượng nhẹ chuẩn chạy quảng cáo.",
    "pipeline_title": "QUY TRÌNH SẢN XUẤT 3 BƯỚC CHUYÊN NGHIỆP",
    "pipeline_desc": "QUY TRÌNH SÁNG TẠO KHÉP KÍN // CHẤT LƯỢNG ĐỒNG NHẤT",
    "role_art": "Bước 01 — Xử Lý Hình Ảnh & Tạo Hình 3D",
    "role_art_desc": "Tách sạch các lớp hình ảnh từ file PSD gốc, dựng khối số 3D '150' phủ nhám lì cùng khung đa giác ánh kim và giữ đường cắt sản phẩm sắc nét.",
    "role_compositor": "Bước 02 — Dàn Trang 11 Kích Thước & Xuất File PSD",
    "role_compositor_desc": "Tự động sắp xếp bố cục hài hòa cho đủ 11 kích thước quảng cáo với đường dẫn vuông góc, nền nối mượt mà và xuất file PSD giữ nguyên tên layer tiếng Hàn dễ chỉnh sửa.",
    "role_qa": "Bước 03 — Kiểm Duyệt Tự Động 15 Tiêu Chuẩn",
    "role_qa_desc": "Kiểm tra chặt chẽ trước khi bàn giao: độ bóng tự nhiên không lóa nhựa (< 0.5%), chữ Hàn Quốc không chồng chéo, chuẩn màu web sRGB và dung lượng mỗi ảnh dưới 800KB.",
    "telemetry_title": "BẢNG KẾT QUẢ KIỂM DUYỆT CHẤT LƯỢNG (CẬP NHẬT TRỰC TIẾP)",
    "rules_passed": "15/15 TIÊU CHUẨN CHẤT LƯỢNG ĐẠT",
    "rule_kerning": "Khoảng cách & độ rõ nét chữ Hàn Quốc",
    "rule_collision": "Không chồng chéo giữa chữ và hình ảnh",
    "rule_anti_plastic": "Bề mặt 3D nhám lì tự nhiên (Không bóng nhựa)",
    "rule_luni": "Tên layer tiếng Hàn hiển thị chuẩn trong Photoshop",
    "rule_layers": "Căn chỉnh gọn gàng đủ 11 kích thước XEXYMIX",
    "rule_weight": "Dung lượng nhẹ (<= 800KB) & 0% Watermark AI",
    "col_rule_id": "MÃ KIỂM TRA",
    "col_gate": "TIÊU CHUẨN KIỂM DUYỆT",
    "col_constraint": "YÊU CẦU",
    "col_measured": "KẾT QUẢ",
    "col_status": "TRẠNG THÁI"
  },
  "manifest_engine": {
    "title": "HỆ THỐNG ĐA THƯƠNG HIỆU // TÁI SỬ DỤNG LINH HOẠT",
    "badge": "CẤU HÌNH CHIẾN DỊCH TẬP TRUNG // ĐA THƯƠNG HIỆU",
    "description": "Toàn bộ hình ảnh, bảng màu thương hiệu và kích thước quảng cáo được quản lý tập trung trong một file cấu hình duy nhất—dễ dàng nhân bản cho mọi thương hiệu mới chỉ trong vài phút.",
    "white_label_desc": "CHIẾN DỊCH HIỆN TẠI: CHAI COMMUNICATION",
    "white_label_active": "ĐANG XEM THỬ THƯƠNG HIỆU MẪU: CHIẾN DỊCH SAMSUNG",
    "btn_toggle_demo": "XEM THỬ THƯƠNG HIỆU KHÁC (DEMO SAMSUNG)",
    "btn_restore_demo": "QUAY LẠI CHIẾN DỊCH CHAI COMMUNICATION",
    "btn_copy_json": "SAO CHÉP FILE CẤU HÌNH",
    "btn_copied_json": "ĐÃ SAO CHÉP VÀO BỘ NHỚ TẠM"
  },
  "footer": {
    "download_title": "KHO TẢI THÀNH PHẨM // BÀI THI CHAI COMMUNICATION",
    "download_desc": "Trọn bộ bàn giao đã kiểm duyệt — Bài 1 (11 ảnh sRGB JPEG sắc nét dưới 800KB) & Bài 2 (2 file PSD Master phân lớp + Ảnh xem trước)",
    "task1_download_label": "BÀI 01 // TRỌN BỘ 11 KÍCH THƯỚC XEXYMIX",
    "task1_card_desc": "11 banner sRGB JPEG chuẩn chạy quảng cáo xuất từ file PSD gốc. Mọi kích thước dưới 800KB, hoàn toàn không có Watermark AI.",
    "task2_download_label": "BÀI 02 // TRỌN BỘ SÁNG TẠO MERITZ",
    "repo_label": "TẢI FILE CẤU HÌNH CHIẾN DỊCH (.JSON)",
    "browse_all_11": "XEM ĐỦ 11 KÍCH THƯỚC"
  },
  "assembly": {
    "status_init": "⚙️ ĐANG KHỞI TẠO BỘ KHUNG...",
    "status_injecting": "⚙️ ĐANG ĐỔ DỮ LIỆU SẢN PHẨM & CHỮ...",
    "status_assembling": "⚙️ ĐANG LẮP RÁP TỰ ĐỘNG...",
    "status_aligned": "✓ ĐÃ KHÓA CHUẨN TỶ LỆ",
    "btn_live_preview": "XEM LẮP RÁP TRỰC TIẾP 11 TỶ LỆ",
    "btn_replay": "▶ Xem Lại Lắp Ráp",
    "modal_ratio_title": "BUỒNG LẮP RÁP TRỰC TIẾP // 11 TỶ LỆ XEXYMIX"
  }
}
  });

  function lookupKey(dict, key) {
    if (!dict || !key) return null;
    const parts = String(key).split('.');
    let node = dict;
    for (let i = 0; i < parts.length; i += 1) {
      if (node && Object.prototype.hasOwnProperty.call(node, parts[i])) {
        node = node[parts[i]];
      } else {
        return null;
      }
    }
    return typeof node === 'string' ? node : null;
  }

  async function loadLocale(lang) {
    const target = SUPPORTED_LANGS.includes(lang) ? lang : DEFAULT_LANG;
    if (localeCache[target]) return localeCache[target];
    try {
      const res = await fetch('./locales/' + target + '.json', { cache: 'no-store' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      localeCache[target] = data;
      return data;
    } catch (_) {
      localeCache[target] = EMBEDDED_LOCALES[target] || EMBEDDED_LOCALES[DEFAULT_LANG];
      return localeCache[target];
    }
  }

  global.AutoBannerI18n = Object.freeze({
    SUPPORTED_LANGS,
    DEFAULT_LANG,
    EMBEDDED_LOCALES,
    loadLocale,
    lookupKey
  });
})(window);
