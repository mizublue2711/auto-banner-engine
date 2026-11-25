/**
 * ============================================================================
 * AUTO-BANNER // ENGINE — Centralized Trilingual Locale Loader & Fallback Map
 * Primary source: ./locales/{ko,en,vi}.json (async fetch)
 * Fallback: Embedded deterministic mirror for local file:// protocol
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
    "xexymix": "02 // XEXYMIX_11",
    "meritz": "03 // MERITZ_3D",
    "telemetry": "04 // PIPELINE_QA",
    "engine": "05 // MANIFEST",
    "download": "DOWNLOAD DELIVERABLES"
  },
  "hero": {
    "title_line1": "AUTO-BANNER",
    "title_highlight": "ENGINE",
    "subtitle": "Deterministic multi-ratio production resizing and parametric creative synthesis governed by strict brand tokens, optical collision guards, and layered PSD delivery.",
    "command_placeholder": "manifest://showcase_manifest.json --verify-all --strict",
    "badge_engine": "ENGINEERING // DETERMINISTIC PIPELINE v1.0.0",
    "system_status": "SYSTEM STATUS: 60 FPS DETERMINISTIC PASS",
    "pill_task1": "TASK 01: 11 RATIOS",
    "pill_task2": "TASK 02: DUAL PSD",
    "pill_qa": "15/15 AUTOMATED GATES PASSED",
    "cad_featured": "FEATURED MASTER // TASK 02 OPTION 2",
    "cad_title": "Monumental 3D Zero-Gravity",
    "cad_inspect_btn": "INSPECT 3D '150' MATTE GRAIN",
    "cad_download_psd": "DOWNLOAD .PSD",
    "cad_safe_zone": "ZERO-COLLISION OPTICAL SAFE ZONE // 0PX DRIFT"
  },
  "hero_hotspots": {
    "pin_aria_prefix": "Inspect hotspot",
    "opt1_tag": "DIRECT RESPONSE // MASTER .PSD",
    "opt1_title": "Option 1 // Conservative Corporate",
    "opt1_desc": "Standard financial direct-response layout featuring a high-contrast 2-column split and metallic 3D gold coin visual hook.",
    "opt1_cta_download": "DOWNLOAD OPTION 1 .PSD",
    "opt2_tag": "INNOVATIVE 3D // MASTER .PSD",
    "opt2_title": "Option 2 // Monumental 3D Zero-Gravity",
    "opt2_desc": "Matte Vermillion '150' monolith suspended inside a Champagne Gold wireframe gem cage with 5 zero-gravity coins.",
    "opt2_cta_download": "DOWNLOAD OPTION 2 .PSD",
    "cta_deep_zoom": "INSPECT DEEP ZOOM",
    "spec_pin_label": "15/15 QA TELEMETRY",
    "spec_tag": "QA TELEMETRY // 15/15 GATES PASSED",
    "spec_title": "Optical Guard & Layered PSD Telemetry",
    "spec_desc": "Verified 100% pass across 15 deterministic gates: anti-plastic specular ceiling (< 0.5%), 0px Korean glyph collision, and UTF-16BE luni PSD layer encoding.",
    "spec_cta_zoom": "INSPECT 3D '150' MATTE GRAIN",
    "spec_cta_download": "DOWNLOAD MASTER .PSD"
  },
  "task1_xexymix": {
    "title": "WORKFLOW A // XEXYMIX 11-RATIO SUITE",
    "badge": "WORKFLOW A // PRODUCTION RESIZING",
    "description": "Orthogonal Manhattan stepping, outer silhouette tangent protection, and non-linear soft alpha feathering across 11 Korean & global ad placements.",
    "feature_orthogonal": "Orthogonal Manhattan Stepping (Zero Slanted Lines)",
    "feature_occlusion": "Zero Fabric Occlusion (Outer Silhouette Tangent)",
    "feature_feathering": "Non-linear Soft Alpha Feathering (Landscape Seam Removal)",
    "feature_watermark": "Policy Compliant: 0% AI Watermark",
    "filter_all": "ALL (11)",
    "filter_vertical": "VERTICAL (4)",
    "filter_square": "SQUARE (2)",
    "filter_wide": "WIDE (2)",
    "filter_micro": "MICRO (3)",
    "toggle_hud": "TOGGLE HUD LASER SPECS",
    "format_spec": "FORMAT: sRGB JPEG (QUALITY 92-95 // STRICTLY <= 800KB)",
    "source_master": "SOURCE MASTER"
  },
  "keepsake": {
    "folder_title": "11-Ratio Archival Suite",
    "folder_hint_open": "[ CLICK TO FAN OUT 11 RATIOS ]",
    "folder_hint_close": "[ COLLAPSE ARCHIVE ]",
    "flip_hint": "HOVER ANY CARD TO FLIP & INSPECT TELEMETRY",
    "items_count_suffix": "RATIOS",
    "label_resolution": "RESOLUTION",
    "label_ratio": "ASPECT RATIO",
    "label_weight": "FILE WEIGHT",
    "label_stepping": "ORTHOGONAL",
    "label_watermark": "AI WATERMARK",
    "status_passed": "PASSED",
    "watermark_compliant": "0% COMPLIANT",
    "footer_verified": "VERIFIED",
    "btn_download_zip": "DOWNLOAD ALL 11 SIZES (.ZIP)"
  },
  "task2_meritz": {
    "title": "WORKFLOW B // MERITZ CREATIVE HOOK",
    "badge": "WORKFLOW B // PARAMETRIC CREATIVE SYNTHESIS",
    "description": "Comparative showcase between Option 1 (Conservative Corporate) and Option 2 (Monumental 3D Zero-Gravity) backed by layered master PSDs.",
    "opt1_title": "OPTION 1 // CONSERVATIVE CORPORATE",
    "opt1_desc": "Direct-response financial layout, 2-column split with metallic 3D gold coin hook.",
    "opt1_eyebrow": "OPTION 01 // DIRECT-RESPONSE CORE",
    "opt1_chip": "7-GROUP LAYERED MASTER",
    "opt2_title": "OPTION 2 // MONUMENTAL 3D ZERO-GRAVITY",
    "opt2_desc": "High-concept low-angle perspective, matte textured red 150 monolith inside Champagne Gold wireframe gem cage, 5 zero-gravity coins with cinematic depth-of-field blur.",
    "opt2_eyebrow": "OPTION 02 // HIGH-CONCEPT 3D CORE",
    "opt2_chip": "3D MONOLITH + GEM CAGE",
    "brand_purity_title": "BRAND PALETTE PURITY WIDGET",
    "brand_purity_desc": "Click any official Meritz hex token to copy to clipboard",
    "brand_purity_badge": "100% PALETTE COMPLIANCE",
    "zoom_instruction": "CLICK TO DEEP-ZOOM MATTE GRAIN",
    "btn_preview_jpg": "PREVIEW .JPG",
    "modal_title": "DEEP-ZOOM MICRO-SURFACE INSPECTOR",
    "modal_eyebrow": "OPTICAL TELEMETRY // 3D '150' MONOLITH",
    "modal_heading": "Matte Grain & Wireframe Cage",
    "modal_desc": "Move cursor across the viewport to inspect the micro-matte diffusion grain on the Vermillion Red (#EF3B24) '150' core, Champagne Gold polyhedral wireframe intersections, and zero-collision Korean typography kerning.",
    "modal_toggle_zoom": "TOGGLE 2.35x / 1.0x ZOOM",
    "modal_download_psd": "DOWNLOAD LAYERED .PSD"
  },
  "under_the_hood": {
    "title": "UNDER THE HOOD // QA TELEMETRY",
    "badge": "SYSTEM ARCHITECTURE // PIPELINE TELEMETRY",
    "description": "Deterministic layer decomposition, LUNI Unicode PSD encoding, optical collision metrics, and bounded worker execution logs.",
    "pipeline_title": "AGENT WORKFLOW PIPELINE SEQUENCE",
    "pipeline_desc": "MULTI-AGENT ORCHESTRATION // DETERMINISTIC PIPELINE",
    "role_art": "Worker Art — Parametric Asset & 3D Surface Synthesis",
    "role_art_desc": "Extracts master PSD layer hierarchies, generates matte-grain 3D '150' monoliths, Champagne Gold polyhedral wireframe cages, and outer-silhouette alpha masks.",
    "role_compositor": "Worker Compositor — Manhattan Reflow & LUNI PSD Assembler",
    "role_compositor_desc": "Executes orthogonal Manhattan stepping across 11 aspect ratios, non-linear landscape seam feathering, and writes binary PSDs with UTF-16BE luni Unicode layer blocks.",
    "role_qa": "Worker QA — 15-Rule Deterministic Gatekeeper",
    "role_qa_desc": "Enforces fail-closed validation on anti-plastic specular highlights (< 0.5%), 0px Korean glyph collision, sRGB profile embedding, and <= 800KB file weight caps.",
    "telemetry_title": "AUTOMATED QA TELEMETRY TABLE (LIVE FROM MANIFEST)",
    "rules_passed": "15/15 AUTOMATED GATES PASSED",
    "rule_kerning": "Korean Typography & Optical Kerning Guard",
    "rule_collision": "Zero-Collision Bounding Box Verification",
    "rule_anti_plastic": "3D Monolith Anti-Plastic Specular Ceiling",
    "rule_luni": "PSD UTF-16BE Unicode Layer Name (luni) Block",
    "rule_layers": "XEXYMIX 11-Ratio Manhattan Orthogonal Stepping",
    "rule_weight": "Delivery Weight & Policy Guard (0% AI Watermark)",
    "col_rule_id": "RULE ID",
    "col_gate": "VERIFICATION GATE",
    "col_constraint": "CONSTRAINT",
    "col_measured": "MEASURED",
    "col_status": "STATUS"
  },
  "manifest_engine": {
    "title": "MANIFEST-DRIVEN WHITE-LABEL ENGINE",
    "badge": "SINGLE SOURCE OF TRUTH // SCHEMA SANDBOX",
    "description": "Live inspection container bound to showcase_manifest.json for deterministic cross-brand configuration and token overrides.",
    "white_label_desc": "CHAI COMMUNICATION PRODUCTION MANIFEST",
    "white_label_active": "WHITE-LABEL MULTI-TENANT SIMULATION ACTIVE",
    "btn_toggle_demo": "PROVE WHITE-LABEL REUSABILITY (SWAP CLIENT PAYLOAD)",
    "btn_restore_demo": "RESTORE CHAI COMMUNICATION MANIFEST",
    "btn_copy_json": "COPY MANIFEST JSON",
    "btn_copied_json": "JSON COPIED TO CLIPBOARD"
  },
  "footer": {
    "download_title": "DELIVERABLES DOCK // CHAI COMMUNICATION ASSIGNMENT",
    "download_desc": "Verified Deterministic Output Package — Task 1 (11x sRGB JPEGs <= 800KB) & Task 2 (Dual Layered Master PSDs + Previews)",
    "task1_download_label": "TASK 01 // WORKFLOW A PACKAGE",
    "task1_card_desc": "11 sRGB JPEG deliverables derived from master PSD. Strictly <= 800KB per placement, 0% AI Watermark.",
    "task2_download_label": "TASK 02 // WORKFLOW B PACKAGE",
    "repo_label": "DOWNLOAD SHOWCASE_MANIFEST.JSON",
    "browse_all_11": "BROWSE ALL 11 PLACEMENTS"
  }
},
    ko: {
  "nav": {
    "overview": "01 // 개요",
    "xexymix": "02 // 젝시믹스_11종",
    "meritz": "03 // 메리츠_3D",
    "telemetry": "04 // 파이프라인_QA",
    "engine": "05 // 매니페스트",
    "download": "성과물 다운로드"
  },
  "hero": {
    "title_line1": "AUTO-BANNER",
    "title_highlight": "ENGINE",
    "subtitle": "엄격한 브랜드 토큰, 광학 충돌 방지 가드, 레이어드 PSD 출력을 기반으로 구축된 Chai Communication 과제용 결정론적 다규격 리사이징 및 크리에이티브 자동화 엔진.",
    "command_placeholder": "manifest://showcase_manifest.json --verify-all --strict",
    "badge_engine": "자동화 엔지니어링 // 결정론적 파이프라인 v1.0.0",
    "system_status": "시스템 상태: 60 FPS 무결성 검증 통과",
    "pill_task1": "과제 01: 11종 규격",
    "pill_task2": "과제 02: 듀얼 PSD",
    "pill_qa": "15/15 자동 검증 관문 통과",
    "cad_featured": "대표 마스터 // 과제 02 2안",
    "cad_title": "무중력 3D 조형물 혁신형",
    "cad_inspect_btn": "3D '150' 매트 질감 확대 검사",
    "cad_download_psd": "원본 .PSD 다운로드",
    "cad_safe_zone": "충돌 제로 광학 안전 영역 // 0PX 오차"
  },
  "hero_hotspots": {
    "pin_aria_prefix": "핫스팟 상세 검증",
    "opt1_tag": "다이렉트 리스폰스 // 마스터 .PSD",
    "opt1_title": "1안 // 150만원 혜택 강조 기본형",
    "opt1_desc": "고대비 2단 분할 금융 레이아웃과 메탈릭 3D 골드 코인 오브제로 즉각적인 시선 유도와 전환율을 극대화한 정통 퍼포먼스 배너.",
    "opt1_cta_download": "1안 원본 .PSD 다운로드",
    "opt2_tag": "하이컨셉 3D // 마스터 .PSD",
    "opt2_title": "2안 // 무중력 3D 모놀리스 혁신형",
    "opt2_desc": "샴페인 골드 다면체 와이어프레임 케이지 내부의 매트 버밀리온 '150' 모놀리스와 5개의 무중력 골드 코인으로 조형미를 극대화한 크리에이티브 마스터.",
    "opt2_cta_download": "2안 원본 .PSD 다운로드",
    "cta_deep_zoom": "매트 질감 확대 검사",
    "spec_pin_label": "15/15 QA 무결성 텔레메트리",
    "spec_tag": "품질 검증 관문 // 15/15 자동 통과",
    "spec_title": "광학 무결성 & 레이어드 PSD 검증 스펙",
    "spec_desc": "안티 플라스틱 반사광 상한(< 0.5%), 한글 글리프 충돌 0px, UTF-16BE(luni) 유니코드 레이어 인코딩 등 15개 자동화 품질 관문을 전수 통과했습니다.",
    "spec_cta_zoom": "3D '150' 매트 질감 확대 검사",
    "spec_cta_download": "마스터 .PSD 다운로드"
  },
  "task1_xexymix": {
    "title": "워크플로우 A // 젝시믹스 11종 규격 매트릭스",
    "badge": "워크플로우 A // 프로덕션 리사이징",
    "description": "국내 및 글로벌 11개 광고 매체 규격 전반에 걸쳐 직교 맨해튼 스태핑, 외곽 실루엣 접선 보호, 비선형 소프트 알파 페더링을 적용했습니다.",
    "feature_orthogonal": "직교 맨해튼 스태핑 (사선 왜곡 0%)",
    "feature_occlusion": "제품 가림 제로 (외곽 실루엣 접선 보호)",
    "feature_feathering": "비선형 소프트 알파 페더링 (가로형 이음매 제거)",
    "feature_watermark": "정책 준수: AI 워터마크 0%",
    "filter_all": "전체 (11)",
    "filter_vertical": "세로형 (4)",
    "filter_square": "정방형 (2)",
    "filter_wide": "가로형 (2)",
    "filter_micro": "마이크로 (3)",
    "toggle_hud": "HUD 레이저 가이드 토글",
    "format_spec": "포맷: sRGB JPEG (품질 92-95 // 800KB 이하 엄수)",
    "source_master": "원본 마스터"
  },
  "keepsake": {
    "folder_title": "11종 규격 아카이브 폴더",
    "folder_hint_open": "[ 클릭하여 11종 규격 펼치기 ]",
    "folder_hint_close": "[ 폴더 접기 ]",
    "flip_hint": "카드에 마우스를 올려 기술 사양 확인",
    "items_count_suffix": "종 규격",
    "label_resolution": "해상도",
    "label_ratio": "종횡비",
    "label_weight": "파일 용량",
    "label_stepping": "직교 스태핑",
    "label_watermark": "AI 워터마크",
    "status_passed": "통과 (PASSED)",
    "watermark_compliant": "0% 준수",
    "footer_verified": "검증 완료",
    "btn_download_zip": "11종 전체 규격 다운로드 (.ZIP)"
  },
  "task2_meritz": {
    "title": "워크플로우 B // 메리츠 크리에이티브 훅",
    "badge": "워크플로우 B // 파라메트릭 크리에이티브 합성",
    "description": "레이어드 마스터 PSD를 기반으로 1안(150만원 강조 기본형)과 2안(무중력 3D 조형물 혁신형)을 나란히 비교 검증합니다.",
    "opt1_title": "1안 // 150만원 강조 기본형",
    "opt1_desc": "직관적인 다이렉트 리스폰스 금융 레이아웃, 2단 분할 구조 및 메탈릭 3D 골드 코인 시선 유도 훅.",
    "opt1_eyebrow": "1안 // 다이렉트 리스폰스 코어",
    "opt1_chip": "7그룹 레이어드 마스터",
    "opt2_title": "2안 // 무중력 3D 조형물 혁신형",
    "opt2_desc": "하이컨셉 로우앵글 원근감, 샴페인 골드 와이어프레임 보석 케이지 내부의 매트 질감 레드 '150' 모놀리스, 시네마틱 심도 블러가 적용된 5개의 무중력 코인.",
    "opt2_eyebrow": "2안 // 하이컨셉 3D 코어",
    "opt2_chip": "3D 모놀리스 + 젬 케이지",
    "brand_purity_title": "브랜드 팔레트 순도 검증 위젯",
    "brand_purity_desc": "메리츠 공식 HEX 토큰을 클릭하면 클립보드에 복사됩니다",
    "brand_purity_badge": "100% 브랜드 팔레트 준수",
    "zoom_instruction": "클릭하여 매트 질감 확대 검사",
    "btn_preview_jpg": "미리보기 .JPG",
    "modal_title": "초정밀 마이크로 표면 확대 검사기",
    "modal_eyebrow": "광학 텔레메트리 // 3D '150' 모놀리스",
    "modal_heading": "매트 그레인 & 와이어프레임 케이지",
    "modal_desc": "뷰포트 위에서 커서를 움직여 버밀리온 레드(#EF3B24) '150' 코어의 마이크로 매트 질감, 샴페인 골드 다면체 와이어프레임 교차점, 한글 타이포그래피 커닝을 정밀 검사하세요.",
    "modal_toggle_zoom": "2.35배 / 1.0배 확대 전환",
    "modal_download_psd": "레이어드 .PSD 다운로드"
  },
  "under_the_hood": {
    "title": "엔진 내부 // 15개 QA 텔레메트리",
    "badge": "시스템 아키텍처 // 파이프라인 텔레메트리",
    "description": "결정론적 레이어 분해, LUNI 유니코드 PSD 인코딩, 광학 충돌 지표 및 멀티 에이전트 실행 로그를 실시간으로 확인합니다.",
    "pipeline_title": "에이전트 워크플로우 파이프라인 시퀀스",
    "pipeline_desc": "멀티 에이전트 오케스트레이션 // 결정론적 파이프라인",
    "role_art": "Worker Art — 파라메트릭 에셋 및 3D 표면 합성",
    "role_art_desc": "마스터 PSD 레이어 계층을 추출하고, 매트 그레인 3D '150' 모놀리스, 샴페인 골드 다면체 와이어프레임 케이지 및 외곽 실루엣 알파 마스크를 생성합니다.",
    "role_compositor": "Worker Compositor — 맨해튼 리플로우 및 LUNI PSD 조립",
    "role_compositor_desc": "11개 종횡비 전반에 직교 맨해튼 스태핑과 비선형 가로형 이음매 페더링을 수행하고, UTF-16BE luni 유니코드 레이어 블록이 포함된 바이너리 PSD를 생성합니다.",
    "role_qa": "Worker QA — 15개 규칙 결정론적 게이트키퍼",
    "role_qa_desc": "안티 플라스틱 반사광(< 0.5%), 한글 글리프 충돌 0px, sRGB 프로파일 임베딩 및 800KB 이하 용량 제한에 대해 실패 차단(Fail-Closed) 검증을 수행합니다.",
    "telemetry_title": "자동화 QA 텔레메트리 테이블 (매니페스트 실시간 연동)",
    "rules_passed": "15/15 자동 검증 관문 통과",
    "rule_kerning": "한글 타이포그래피 및 광학 커닝 가드",
    "rule_collision": "바운딩 박스 충돌 제로 검증",
    "rule_anti_plastic": "3D 모놀리스 안티 플라스틱 반사광 상한",
    "rule_luni": "PSD UTF-16BE 유니코드 레이어명(luni) 블록",
    "rule_layers": "젝시믹스 11종 맨해튼 직교 스태핑 검증",
    "rule_weight": "납품 용량 및 정책 가드 (AI 워터마크 0%)",
    "col_rule_id": "규칙 ID",
    "col_gate": "검증 관문",
    "col_constraint": "기준치",
    "col_measured": "측정값",
    "col_status": "상태"
  },
  "manifest_engine": {
    "title": "매니페스트 기반 화이트라벨 엔진",
    "badge": "단일 진실 공급원 // 스키마 샌드박스",
    "description": "showcase_manifest.json에 직접 바인딩되어 타 브랜드 설정 및 디자인 토큰 교체만으로 즉시 재사용 가능한 라이브 인스펙터입니다.",
    "white_label_desc": "Chai Communication 프로덕션 매니페스트",
    "white_label_active": "화이트라벨 멀티 테넌트 시뮬레이션 활성",
    "btn_toggle_demo": "화이트라벨 재사용성 검증 (클라이언트 페이로드 교체)",
    "btn_restore_demo": "Chai Communication 매니페스트 복원",
    "btn_copy_json": "매니페스트 JSON 복사",
    "btn_copied_json": "클립보드에 복사 완료"
  },
  "footer": {
    "download_title": "성과물 도크 // CHAI COMMUNICATION 과제",
    "download_desc": "검증 완료된 결정론적 납품 패키지 — 과제 1 (sRGB JPEG 11종, 800KB 이하) 및 과제 2 (듀얼 레이어드 마스터 PSD + 미리보기)",
    "task1_download_label": "과제 01 // 워크플로우 A 패키지",
    "task1_card_desc": "원본 마스터 PSD에서 추출된 11종 sRGB JPEG 성과물. 모든 규격 800KB 이하, AI 워터마크 0% 준수.",
    "task2_download_label": "과제 02 // 워크플로우 B 패키지",
    "repo_label": "SHOWCASE_MANIFEST.JSON 다운로드",
    "browse_all_11": "11종 전체 규격 보기"
  }
},
    vi: {
  "nav": {
    "overview": "01 // TỔNG QUAN",
    "xexymix": "02 // XEXYMIX_11",
    "meritz": "03 // MERITZ_3D",
    "telemetry": "04 // KIỂM THỬ_QA",
    "engine": "05 // MANIFEST",
    "download": "TẢI TOÀN BỘ THÀNH PHẨM"
  },
  "hero": {
    "title_line1": "AUTO-BANNER",
    "title_highlight": "ENGINE",
    "subtitle": "Hệ thống tự động hóa co giãn đa kích thước và sản xuất banner sáng tạo đa tầng cho bài thi Chai Communication, vận hành bằng brand token nghiêm ngặt, lớp chống va chạm quang học và xuất file PSD đa lớp.",
    "command_placeholder": "manifest://showcase_manifest.json --verify-all --strict",
    "badge_engine": "KỸ THUẬT TỰ ĐỘNG HÓA // PIPELINE v1.0.0",
    "system_status": "TRẠNG THÁI: VƯỢT QUA KIỂM THỬ 60 FPS",
    "pill_task1": "BÀI 01: 11 TỶ LỆ",
    "pill_task2": "BÀI 02: 2 BẢN PSD",
    "pill_qa": "15/15 BÀI TEST TỰ ĐỘNG ĐẠT CHUẨN",
    "cad_featured": "BẢN MASTER TIÊU BIỂU // BÀI 02 OPTION 2",
    "cad_title": "Khối 3D Không Trọng Lực Đột Phá",
    "cad_inspect_btn": "SOI KÍNH LÚP ĐỘ NHÁM LÌ 3D '150'",
    "cad_download_psd": "TẢI FILE .PSD",
    "cad_safe_zone": "VÙNG AN TOÀN QUANG HỌC KHÔNG VA CHẠM // SAI SỐ 0PX"
  },
  "hero_hotspots": {
    "pin_aria_prefix": "Xem điểm tương tác",
    "opt1_tag": "CHUYỂN ĐỔI TRỰC TIẾP // MASTER .PSD",
    "opt1_title": "Option 1 // Phương Án Doanh Nghiệp Chuẩn Mực",
    "opt1_desc": "Bố cục tài chính chuyển đổi trực tiếp với cấu trúc chia 2 cột tương phản cao kết hợp đồng xu vàng 3D ánh kim thu hút thị giác.",
    "opt1_cta_download": "TẢI .PSD OPTION 1",
    "opt2_tag": "ĐỘT PHÁ 3D // MASTER .PSD",
    "opt2_title": "Option 2 // Khối 3D Không Trọng Lực Đột Phá",
    "opt2_desc": "Khối '150' đỏ Vermillion nhám lì lơ lửng trong lồng khung dây đa diện vàng Champagne cùng 5 đồng xu không trọng lực.",
    "opt2_cta_download": "TẢI .PSD OPTION 2",
    "cta_deep_zoom": "SOI KÍNH LÚP 3D",
    "spec_pin_label": "15/15 TELEMETRY KIỂM ĐỊNH QA",
    "spec_tag": "TELEMETRY QA // 15/15 CỔNG ĐẠT CHUẨN",
    "spec_title": "Thông Số Kiểm Định Quang Học & PSD Phân Lớp",
    "spec_desc": "Vượt qua 15/15 cổng kiểm định tự động: giới hạn phản xạ chống bóng nhựa (< 0.5%), 0px va chạm chữ Hàn Quốc và mã hóa tên layer PSD chuẩn UTF-16BE (luni).",
    "spec_cta_zoom": "SOI KÍNH LÚP ĐỘ NHÁM LÌ 3D '150'",
    "spec_cta_download": "TẢI FILE MASTER .PSD"
  },
  "task1_xexymix": {
    "title": "QUY TRÌNH A // BỘ BANNER XEXYMIX 11 TỶ LỆ",
    "badge": "QUY TRÌNH A // CO GIÃN ĐA KÍCH THƯỚC",
    "description": "Áp dụng bước nhảy trực giao Manhattan, bảo vệ đường viền tiếp tuyến sản phẩm và làm mờ alpha phi tuyến tính trên toàn bộ 11 vị trí quảng cáo Hàn Quốc & toàn cầu.",
    "feature_orthogonal": "Bước nhảy trực giao Manhattan (0% đường chéo lệch)",
    "feature_occlusion": "Không che khuất sản phẩm (Bảo vệ viền tiếp tuyến)",
    "feature_feathering": "Làm mờ alpha phi tuyến (Xóa mối nối banner ngang)",
    "feature_watermark": "Tuân thủ chính sách: 0% Watermark AI",
    "filter_all": "TẤT CẢ (11)",
    "filter_vertical": "DỌC (4)",
    "filter_square": "VUÔNG (2)",
    "filter_wide": "NGANG (2)",
    "filter_micro": "SIÊU NHỎ (3)",
    "toggle_hud": "BẬT/TẮT TIA LASER HUD",
    "format_spec": "ĐỊNH DẠNG: sRGB JPEG (CHẤT LƯỢNG 92-95 // NGHIÊM NGẶT <= 800KB)",
    "source_master": "FILE GỐC MASTER"
  },
  "keepsake": {
    "folder_title": "Thư Mục Lưu Trữ 11 Tỷ Lệ",
    "folder_hint_open": "[ NHẤN ĐỂ XÒE 11 TỶ LỆ ]",
    "folder_hint_close": "[ THU GỌN THƯ MỤC ]",
    "flip_hint": "RÊ CHUỘT VÀO THẺ ĐỂ LẬT XEM THÔNG SỐ",
    "items_count_suffix": "TỶ LỆ",
    "label_resolution": "ĐỘ PHÂN GIẢI",
    "label_ratio": "TỶ LỆ KHUNG",
    "label_weight": "DUNG LƯỢNG",
    "label_stepping": "BƯỚC TRỰC GIAO",
    "label_watermark": "WATERMARK AI",
    "status_passed": "ĐẠT (PASSED)",
    "watermark_compliant": "0% TUÂN THỦ",
    "footer_verified": "ĐÃ KIỂM ĐỊNH",
    "btn_download_zip": "TẢI TOÀN BỘ 11 KÍCH THƯỚC (.ZIP)"
  },
  "task2_meritz": {
    "title": "QUY TRÌNH B // BANNER SÁNG TẠO MERITZ",
    "badge": "QUY TRÌNH B // TỔNG HỢP SÁNG TẠO THAM SỐ",
    "description": "So sánh trực tiếp giữa Option 1 (Phương án an toàn doanh nghiệp) và Option 2 (Khối 3D không trọng lực đột phá), đi kèm đầy đủ file PSD gốc phân lớp.",
    "opt1_title": "OPTION 1 // PHƯƠNG ÁN AN TOÀN DOANH NGHIỆP",
    "opt1_desc": "Bố cục tài chính chuyển đổi trực tiếp, chia 2 cột rõ ràng kết hợp đồng xu vàng 3D ánh kim thu hút thị giác.",
    "opt1_eyebrow": "OPTION 01 // CHUYỂN ĐỔI TRỰC TIẾP",
    "opt1_chip": "MASTER 7 NHÓM LAYER",
    "opt2_title": "OPTION 2 // KHỐI 3D KHÔNG TRỌNG LỰC ĐỘT PHÁ",
    "opt2_desc": "Góc nhìn thấp giàu tính biểu tượng, khối '150' đỏ lì đặt trong lồng đa diện vàng Champagne, 5 đồng xu lơ lửng không trọng lực với hiệu ứng xóa phông điện ảnh.",
    "opt2_eyebrow": "OPTION 02 // KHỐI 3D ĐỘT PHÁ",
    "opt2_chip": "KHỐI 3D + LỒNG ĐA DIỆN",
    "brand_purity_title": "BẢNG KIỂM TRA ĐỘ THUẦN MÀU THƯƠNG HIỆU",
    "brand_purity_desc": "Nhấn vào bất kỳ mã màu HEX chính thức nào của Meritz để sao chép",
    "brand_purity_badge": "TUÂN THỦ 100% BẢNG MÀU",
    "zoom_instruction": "CLICK ĐỂ SOI KÍNH LÚP ĐỘ NHÁM LÌ",
    "btn_preview_jpg": "XEM TRƯỚC .JPG",
    "modal_title": "KÍNH LÚP SOI VI BỀ MẶT 3D",
    "modal_eyebrow": "ĐO QUANG HỌC // KHỐI 3D '150'",
    "modal_heading": "Độ Nhám Lì & Lồng Khung Dây",
    "modal_desc": "Di chuyển chuột trên khung hình để kiểm tra hạt nhám lì vi mô trên khối đỏ Vermillion (#EF3B24) '150', các điểm giao khung dây vàng Champagne và khoảng cách chữ Hàn Quốc không va chạm.",
    "modal_toggle_zoom": "CHUYỂN ĐỔI ZOOM 2.35x / 1.0x",
    "modal_download_psd": "TẢI FILE .PSD PHÂN LỚP"
  },
  "under_the_hood": {
    "title": "CHI TIẾT KỸ THUẬT // BẢNG ĐO TELEMETRY QA",
    "badge": "KIẾN TRÚC HỆ THỐNG // TELEMETRY PIPELINE",
    "description": "Phân tách layer xác định, mã hóa tên layer tiếng Hàn LUNI Unicode trong PSD, chỉ số va chạm quang học và nhật ký điều phối đa tác nhân.",
    "pipeline_title": "CHUỖI QUY TRÌNH ĐA TÁC NHÂN (MULTI-AGENT)",
    "pipeline_desc": "ĐIỀU PHỐI ĐA TÁC NHÂN // PIPELINE XÁC ĐỊNH",
    "role_art": "Worker Art — Tổng hợp tài sản tham số & bề mặt 3D",
    "role_art_desc": "Trích xuất cây layer từ PSD gốc, tạo khối 3D '150' phủ nhám lì, lồng khung dây đa diện vàng Champagne và mặt nạ alpha bám sát viền sản phẩm.",
    "role_compositor": "Worker Compositor — Dàn trang Manhattan & đóng gói PSD LUNI",
    "role_compositor_desc": "Thực thi bước nhảy trực giao Manhattan trên 11 tỷ lệ, làm mờ mối nối phi tuyến và xuất file PSD nhị phân tích hợp khối tên layer Unicode UTF-16BE (luni).",
    "role_qa": "Worker QA — Cổng kiểm duyệt tự động 15 quy tắc",
    "role_qa_desc": "Áp đặt kiểm định fail-closed cho độ bóng chống nhựa (< 0.5%), va chạm ký tự Hàn Quốc 0px, nhúng hồ sơ màu sRGB và giới hạn dung lượng <= 800KB.",
    "telemetry_title": "BẢNG TELEMETRY QA TỰ ĐỘNG (ĐỒNG BỘ TỪ MANIFEST)",
    "rules_passed": "15/15 BÀI TEST TỰ ĐỘNG ĐẠT CHUẨN",
    "rule_kerning": "Kiểm soát khoảng cách & chữ Hàn Quốc",
    "rule_collision": "Xác minh hộp giới hạn không va chạm",
    "rule_anti_plastic": "Ngưỡng chống bóng nhựa trên khối 3D",
    "rule_luni": "Khối tên layer Unicode UTF-16BE (luni) trong PSD",
    "rule_layers": "Bước nhảy trực giao Manhattan 11 tỷ lệ XEXYMIX",
    "rule_weight": "Kiểm soát dung lượng & chính sách (0% Watermark AI)",
    "col_rule_id": "MÃ LUẬT",
    "col_gate": "CỔNG KIỂM ĐỊNH",
    "col_constraint": "TIÊU CHUẨN",
    "col_measured": "ĐO ĐƯỢC",
    "col_status": "TRẠNG THÁI"
  },
  "manifest_engine": {
    "title": "HỆ THỐNG WHITE-LABEL ĐIỀU KHIỂN BẰNG MANIFEST",
    "badge": "NGUỒN DỮ LIỆU DUY NHẤT // SANDBOX SCHEMA",
    "description": "Khung kiểm tra trực tiếp gắn với showcase_manifest.json, chứng minh khả năng tái sử dụng cho mọi thương hiệu chỉ bằng việc thay đổi cấu hình.",
    "white_label_desc": "MANIFEST SẢN XUẤT CHAI COMMUNICATION",
    "white_label_active": "ĐANG CHẠY MÔ PHỎNG ĐA THƯƠNG HIỆU (WHITE-LABEL)",
    "btn_toggle_demo": "CHỨNG MINH TÁI SỬ DỤNG WHITE-LABEL (ĐỔI PAYLOAD)",
    "btn_restore_demo": "KHÔI PHỤC MANIFEST CHAI COMMUNICATION",
    "btn_copy_json": "SAO CHÉP MANIFEST JSON",
    "btn_copied_json": "ĐÃ SAO CHÉP VÀO CLIPBOARD"
  },
  "footer": {
    "download_title": "KHO TẢI THÀNH PHẨM // BÀI THI CHAI COMMUNICATION",
    "download_desc": "Gói bàn giao đã qua kiểm định tự động — Bài 1 (11 ảnh sRGB JPEG <= 800KB) & Bài 2 (2 file PSD Master phân lớp + Ảnh xem trước)",
    "task1_download_label": "BÀI 01 // GÓI THÀNH PHẨM QUY TRÌNH A",
    "task1_card_desc": "11 thành phẩm sRGB JPEG xuất từ file PSD gốc. Nghiêm ngặt <= 800KB mỗi ảnh, 0% Watermark AI.",
    "task2_download_label": "BÀI 02 // GÓI THÀNH PHẨM QUY TRÌNH B",
    "repo_label": "TẢI SHOWCASE_MANIFEST.JSON",
    "browse_all_11": "XEM TOÀN BỘ 11 KÍCH THƯỚC"
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
