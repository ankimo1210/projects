import Foundation
import UserNotifications

/// 毎日決まった時刻にリマインド通知を送るサービス（固定時刻・MVP版）
enum NotificationService {
    private static let reminderIdentifier = "dailyReminder"

    static func requestAuthorization() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { _, error in
            if let error {
                print("⚠️ 通知の許可リクエストに失敗しました: \(error)")
            }
        }
    }

    /// - Parameters:
    ///   - hour: 通知時刻（時）。MVPでは固定値（デフォルト20時）。
    ///   - minute: 通知時刻（分）
    static func scheduleDailyReminder(hour: Int = 20, minute: Int = 0) {
        let center = UNUserNotificationCenter.current()
        center.removePendingNotificationRequests(withIdentifiers: [reminderIdentifier])

        let content = UNMutableNotificationContent()
        content.title = "英単語の時間です📖"
        content.body = "今日の分の単語クイズに挑戦しましょう！"
        content.sound = .default

        var dateComponents = DateComponents()
        dateComponents.hour = hour
        dateComponents.minute = minute

        let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: true)
        let request = UNNotificationRequest(identifier: reminderIdentifier, content: content, trigger: trigger)

        center.add(request) { error in
            if let error {
                print("⚠️ 通知のスケジュールに失敗しました: \(error)")
            }
        }
    }
}
