# CruNote Atlas UX Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development for independent bounded work and review. User-approved scope is fixed; no further approval checkpoint is needed for reversible implementation in this plan.

**Goal:** 地図・実在産地の写真・因果説明・演習をつなぐフランス10産地のオフライン図鑑を実装する。

**Architecture:** 既存のRegionMapStoreと比較プロフィールを再利用。写真は独立したメディアカタログとして追加する。探索ホーム、産地詳細、解説からの地域リンクを小さな共有SwiftUIコンポーネントで構成する。

**Tech Stack:** SwiftUI / SwiftData (iOS 17+), Python standard library, local JPEG / SVG assets.

**Spec:** docs/atlas-ux-design.md

## Global Constraints

- iOS 17以上、日本語、オフライン利用。
- 追加の本番依存、外部API、SwiftDataスキーマ変更を行わない。
- フランス10産地のID・問題・用語・学習履歴・無料権限を保持する。
- 作者、写真原典、ライセンス、加工内容を表示する。写真欠落でも学習できる。
- 作業用worktreeで実装。元プロジェクトへの反映はハッシュ比較した差分のみ。commit / push / deployは行わない。
- iOSビルドを実行できたと主張しない。

## Task 1: 実写素材の収集

**Files:** ReferenceSources/AtlasMedia/manifest.json; ReferenceSources/AtlasMedia/*.jpg
**Interface:** schemaVersion=1, photos=[{regionID,assetName,filename,title,altText,author,sourceURL,license,licenseURL,changes,checkedAt}]. 10産地各1画像。写真は商用再配布可能なCC0 / CC BY / CC BY-SA等に限定。

- [x] Commons等の原典ページで撮影場所・作者・利用条件を検証。
- [x] 各画像を長辺1280px以下のJPEGとして保存し、加工内容を記録。
- [x] 写真とメタデータを目視・機械検査し、10項目の対応表を残す。

## Task 2: 再現可能な地図とメディアパック

**Files:** scripts/build_atlas_media.py; scripts/tests/test_build_atlas_media.py; WSET/AtlasData/atlas_media.json; WSET/Assets.xcassets/AtlasPhotos/; ReferenceSources/RegionMaps/france.svg; ReferenceSources/wset_region_map_master.json
**Interface:** atlas_media.json contains the same photos array plus sourceHash and sha256/width/height for each photo. Existing RegionMap schema remains v2.

- [x] Test missing credits, broken region IDs, tampered asset bytes, and generated-file drift before implementing validation.
- [x] Validate source manifest and JPEG headers, build deterministic catalog copies, add `--check` to Makefile.
- [x] Download Natural Earth country geometry; preserve source provenance and a deterministic local rendering script. Use one common projection for map paths and normalized pins.
- [x] Rebuild region map and content-review packet; verify fixed geography and image dimensions.

## Task 3: 探索と産地図鑑の画面

**Files:** WSET/AppTheme.swift; WSET/ContentView.swift; WSET/Views/HomeView.swift; WSET/Views/AtlasViews.swift; WSET/Views/RegionMapViews.swift; WSET/Data/AtlasMediaStore.swift
**Interfaces:** AtlasMediaStore.shared.photo(for regionID: String) -> AtlasPhoto?; RegionPhotoView(regionID: String); RegionMapCanvasView uses document, selectedRegionID and onSelect (all internal callers updated); RegionDetailView retains region/country initializer.

- [x] Parse bundled photo catalog without network; expose failure-safe optional lookup.
- [x] Provide semantic paper / forest / wine colors with dark-mode variants.
- [x] Replace home statistics with map/list exploration, selected region preview, and study entry through region detail.
- [x] Use photo-led region detail, native tabs for existing comparison facts, source disclosure, comparison and existing 10/20-question sessions.
- [x] Preserve existing navigation and accessibility identifiers where possible, adding atlas-specific identifiers.

## Task 4: 学習から地図へ戻る

**Files:** WSET/Views/StudySessionView.swift; WSET/Views/QuestionDetailView.swift; WSET/Views/AtlasViews.swift; WSETUITests/AtlasUITests.swift; existing tab-dependent UI tests
**Interface:** QuestionRegionLinksView(question: StudyQuestion) uses structured question geography and existing RegionStudyQuery matching / entitlement policy.

- [x] Show related-region entry only after answer reveal in practice; detail can link with the same revealed state.
- [x] Open the matching country map with the region selected; preserve the ongoing question state.
- [x] Add UI tests for explore → detail → practice, answer → atlas → return, photo credits, map/list switching, map-marker selection, and data-load fallback. Authored only; Xcode unavailable.

## Task 5: 検証と反映

- [x] Run new targeted tests, then `make verify`; inspect photo contact sheet and rendered map. 71 Python tests and all generated checks passed; 10 photos fully decoded and visually checked.
- [x] Perform a separate static review of SwiftUI API usage, access policy and navigation; resolve important findings. The shared dark wine tint reduced contrast on existing prominent buttons; those controls now use wineAction.
- [x] `git diff --check`; compare original source hashes before transferring only changed files. All 78 copied files hash-verified, with a local backup.
- [x] Run generated-content verification in the real project and report what remains untested on iOS. All generated checks passed; Swift/Xcode execution remains unavailable as documented in atlas-ux-validation.md.
