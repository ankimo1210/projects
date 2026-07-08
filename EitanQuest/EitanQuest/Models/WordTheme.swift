import SwiftUI

/// 単語の意味テーマ（カテゴリ=難易度とは別の、意味のグルーピング）。
/// 同じテーマ×同じ品詞から「惜しい」ハズレ選択肢を選ぶのに使い、テーマ別の閲覧/出題にも使う。
enum WordTheme: String, CaseIterable, Identifiable, Hashable {
    case emotion, personality, time, money, work, study, communication
    case food, home, shopping, travel, weather, health, people
    case action, quality, quantity, society

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .emotion: return "感情"
        case .personality: return "性格・態度"
        case .time: return "時間・予定"
        case .money: return "お金・金融"
        case .work: return "仕事・ビジネス"
        case .study: return "学習・思考"
        case .communication: return "伝える・話す"
        case .food: return "食事・料理"
        case .home: return "家・暮らし"
        case .shopping: return "買い物"
        case .travel: return "旅行・移動"
        case .weather: return "天気・自然"
        case .health: return "健康・体"
        case .people: return "人・関係"
        case .action: return "動作・行動"
        case .quality: return "性質・程度"
        case .quantity: return "量・変化"
        case .society: return "社会・ルール"
        }
    }

    var symbolName: String {
        switch self {
        case .emotion: return "face.smiling"
        case .personality: return "person.fill"
        case .time: return "clock.fill"
        case .money: return "yensign.circle.fill"
        case .work: return "briefcase.fill"
        case .study: return "book.fill"
        case .communication: return "bubble.left.and.bubble.right.fill"
        case .food: return "fork.knife"
        case .home: return "house.fill"
        case .shopping: return "cart.fill"
        case .travel: return "airplane"
        case .weather: return "cloud.sun.fill"
        case .health: return "heart.fill"
        case .people: return "person.2.fill"
        case .action: return "figure.run"
        case .quality: return "star.fill"
        case .quantity: return "chart.bar.fill"
        case .society: return "building.columns.fill"
        }
    }

    var tint: Color {
        switch self {
        case .emotion: return .pink
        case .personality: return .purple
        case .time: return .blue
        case .money: return .green
        case .work: return .teal
        case .study: return .indigo
        case .communication: return .cyan
        case .food: return .orange
        case .home: return .brown
        case .shopping: return .mint
        case .travel: return .blue
        case .weather: return .cyan
        case .health: return .red
        case .people: return .purple
        case .action: return .orange
        case .quality: return .yellow
        case .quantity: return .teal
        case .society: return .indigo
        }
    }
}
