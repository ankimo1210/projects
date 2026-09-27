# HSK 3級・最初の単元の実装

承認済みの商品設計のうち、最初の検証可能な学習体験を実装する。購入・公開・全級展開は後続。詳細な商品設計は本タスクの outputs/my-tianjin-product-roadmap.md にある。

## Global Constraints

- Japanese learner-facing copy. Keep existing free tabs, stable vocabulary IDs, and existing histories intact.
- Work only in My Tianjin on branch codex/hsk3-first-lesson. No production dependencies, remote operations, publishing, or destructive migrations.
- One original 20-question draft unit: 時間・場所の語順. It is an HSK 3級 learning prototype, not an official mock exam. Clearly display 監修前 and 試験形式との対応は確認中. Do not claim verified syllabus coverage or human review.
- Use the existing ReviewScheduler. Keep course progress separate from vocabulary and self-assessment statistics.
- Save before moving forward. A failed save keeps the answer and question in place; retry must not double-count. Restore the active question and submitted explanation after restart.
- Swift/Xcode are unavailable on this host. Add meaningful XCTest coverage and document it as not executed. Run executable Node content validation with malformed fixture tests. Do not replace Swift behavior tests with source-text assertions.
- No paid product, purchase claim, pass probability, diagnostic-score claim, or external analytics in this milestone.

## Shared JSON interface (root authors content)

Resource: My Tianjin/Resources/Content/hsk3-first-lesson.json (a bundled JSON file; try Resources/Content, Content, and bundle root, as existing packaging may flatten resources).

Root keys: schemaVersion (1), id (hsk3-first-lesson), contentVersion (2026-09-15-draft1), title (時間・場所の語順), subtitle, reviewStatus (draft), examProfile { id: hsk3-prototype-unconfirmed, targetLevel: 3, syllabusStatus: unconfirmed, note }, questions (20).

Each question: id, topic (time or place), prompt (Japanese), options [{id, text, explanation}], correctOptionID, explanation (Japanese rule), example {hanzi, pinyin, japanese}. IDs and option order are stable. Exactly one answer key and three unique options per question. Each option explains its own distinction. No diagnostic or held-out evaluation questions in this asset.

## Task 1: Course core and atomic persistence

Files to create:
- My Tianjin/Core/Course/CourseModels.swift
- My Tianjin/Core/Course/CourseEngine.swift
- My Tianjin/Content/CourseRepository.swift
- My Tianjin/Data/CourseStore.swift
- My TianjinTests/CourseEngineTests.swift
- My TianjinTests/CourseStoreTests.swift
- My TianjinTests/CourseContentTests.swift

Core Codable value types (nonisolated, following existing project style): CourseLesson, CourseQuestion, CourseOption, CourseExample, CourseExamProfile matching the JSON. CourseLesson validates supported schema/draft profile, nonempty IDs/text, unique IDs/options, matching correct answer, and nonempty explanations/examples. Fail visibly for malformed or unsupported content; do not silently substitute unrelated vocabulary.

CourseSnapshot: schemaVersion, courseID, contentVersion, progress [String: StudyItemProgress], attempts [CourseAttempt], sessions [CourseSession]. Store course/version on the snapshot; incompatible or corrupt saved data must throw without overwriting. CourseAttempt: id UUID, sessionID UUID, questionID, selectedOptionID, isCorrect, answeredAt Date, isReview Bool. CourseSession: id UUID, questionIDs [String], currentIndex Int, startedAt Date, completedAt Date?, attempts [CourseAttempt]. Submitted current answer is represented by an attempt at currentIndex until explicit advance. Keep completed sessions for a truthful result; no fabricated totals.

CourseEngine functions, pure values:
- makeSession(lesson: CourseLesson, progress: [String: StudyItemProgress], minutes: Int, reviewOnly: Bool, now: Date) -> CourseSession?: 3 or 10 questions max, estimated one minute each; due questions first ordered by dueAt then source order; then unanswered questions in source order; never include future-due answered questions just to fill quota. Return nil when nothing eligible. Restrict IDs to this lesson. reviewOnly selects only due questions. Fixed source option order ensures reproducible restart.
- submit(snapshot: CourseSnapshot, lesson: CourseLesson, sessionID: UUID, attemptID: UUID, optionID: String, now: Date) throws -> CourseSnapshot: reject invalid session/question/option or second different answer; same attempt UUID retry is a no-op only when identity/payload agrees; use scheduler exactly once and keep current index until advance.
- advance(snapshot: CourseSnapshot, sessionID: UUID, now: Date) throws -> CourseSnapshot: requires current answer; increment index, mark completed after last question. Active session is the last uncompleted session.

Expose pragmatic conveniences to Task 2: lesson.question(id:), snapshot.activeSession, session.currentQuestionID, session.currentAttempt, session.correctCount. Document final exact signatures in report if minor adjustments help correctness.

CourseStore (@MainActor ObservableObject): @Published private(set) lesson: CourseLesson?, snapshot: CourseSnapshot?, errorMessage: String?; init(); load(in container: ModelContainer); start(minutes: Int, reviewOnly: Bool = false); submit(optionID: String); advance(); clearError(). Methods return Bool for success where useful. It loads resource via CourseRepository and retains a dedicated ModelContext with autosave disabled, isolating rollback from other screens. Persist one Codable snapshot in EXISTING StudySessionRecord under scopeKey course::hsk3-first-lesson (no SwiftData model additions). Encode candidate, update/insert, context.save(), then publish. On failure rollback this dedicated context and retain previous snapshot; UI retains selected option. Use stable attempt ID for retries. Include an injected save action/data loader only if meaningful failure tests need it; avoid test-only production behavior.

Tests first: due-before-new with cap, no future-due padding, unrelated progress excluded, deterministic order, empty review, wrong answer schedules 10 minutes, correct schedules one day, duplicate UUID idempotence and conflict rejection, cannot advance without answer, completed and active session JSON roundtrip including submitted explanation, same-version resume, incompatible snapshot rejection, real in-memory SwiftData save/reload and failure rollback/retry without duplicate counts. Test corrupt JSON and invalid answer references. Run if toolchain becomes available; otherwise report unexecuted precisely.

## Task 2: Today and lesson UI

Files:
- Create My Tianjin/Features/Course/CourseTodayView.swift
- Create My Tianjin/Features/Course/CourseSessionView.swift
- Modify My Tianjin/ContentView.swift (tab 0 only)
- Existing HomeView becomes reachable as 学習メニュー from Today; all other tabs stay at current indices.

Read Task 1 interface report. Today owns @StateObject CourseStore and loads using modelContext.container. Display HSK 3級を目指す, 先行体験, title, draft/profile note, an honest completed count / unit count from course progress, due count, segmented 3分/10分 selection, 今日の学習 or 続きから, and 期限の来た問題を復習. Keep start unavailable until valid data; failures show message + retry; no due items show next planned date or learning completed state. Time estimates must be labelled 目安 and actual session question count shown. No invented exam date/countdown, weakpoint or mastery claims. Count 20 answers as learning, not proof of mastery. Empty first use invites start, not meaningless performance percentages.

Navigate to CourseSessionView observing the same store. Questions use spacious stacked option buttons with clear selected state, confirm button, progress fraction. Persist confirmation before showing selected-specific explanation, correct sentence, pinyin, Japanese translation, and system Chinese speech (existing SpeechService at normal/slow). Submit/advance errors stay on the same question and offer retry. Disable selecting a different option after submission. Next moves only after advance succeeds. Back leaves session resumable. Reload submitted explanation without reselection. Last question shows result with correct / attempted and future review information; no auto-created new session after completion. Return to Today explicitly.

Semantic fonts, system surfaces, one teal accent, accessible contrast, no fixed card height, full-width readable options, text+icons for correctness, VoiceOver labels for Chinese text and progress. Stop speech on departure/question transition. UI preview may be illustrative but cannot be reported as simulator verification. Use no new dependencies. Do not modify purchase/App Store metadata or existing self-assessment behavior.

## Task 3: Delivery validation (controller)

- Root authors the 20-question JSON and a Node validator with negative fixture tests. Verify IDs, correct answer references, explanation coverage and unsupported profile rejection. Review language as a draft; human signoff remains pending.
- Node existing content validator + self-test, new validator tests, git diff --check, scoped change review.
- Independent task review and final whole-change review, fixing important findings within at most three repair attempts per user instruction.
- Update README and Docs/HSK3FirstLesson.md: implementation scope, storage isolation, saved data version behavior, exact Mac commands, manual checks for offline, interrupted explanation, save failure, 3/10 minutes, no due items, accessibility, and release gates.
- Deliver a patch and a short implementation note in outputs with branch/worktree paths and explicit Xcode/build/editorial limitations. Do not merge/push or remove worktree automatically.
