import SwiftUI

/// 単語のジャンル・レベル分類
enum WordCategory: String, Codable, CaseIterable, Identifiable, Hashable {
    case daily
    case business
    case exam

    var id: String { rawValue }

    /// 画面表示用の日本語名
    var displayName: String {
        switch self {
        case .daily: return "日常会話"
        case .business: return "TOEIC・ビジネス英語"
        case .exam: return "大学受験・英検"
        }
    }

    /// カード等で使うSFシンボル名
    var symbolName: String {
        switch self {
        case .daily: return "sun.max.fill"
        case .business: return "briefcase.fill"
        case .exam: return "graduationcap.fill"
        }
    }

    /// カテゴリを識別するアクセントカラー
    var tint: Color {
        switch self {
        case .daily: return .orange
        case .business: return .teal
        case .exam: return .indigo
        }
    }
}
