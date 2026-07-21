import Foundation
import SwiftData
import UserNotifications

@MainActor
enum ReviewNotificationService {
    static let enabledKey = "reviewNotificationsEnabled"
    private static let dailyIdentifier = "wset.review.daily"
    private static let nextDueIdentifier = "wset.review.nextDue"

    static func requestAndSchedule(progressRecords: [QuestionProgress]) async throws {
        let center = UNUserNotificationCenter.current()
        let granted = try await center.requestAuthorization(options: [.alert, .sound, .badge])
        guard granted else { throw ReviewNotificationError.permissionDenied }
        UserDefaults.standard.set(true, forKey: enabledKey)
        await schedule(progressRecords: progressRecords)
    }

    static func disable() async {
        UserDefaults.standard.set(false, forKey: enabledKey)
        UNUserNotificationCenter.current().removePendingNotificationRequests(
            withIdentifiers: [dailyIdentifier, nextDueIdentifier]
        )
    }

    static func refreshIfEnabled(progressRecords: [QuestionProgress]) async {
        guard UserDefaults.standard.bool(forKey: enabledKey) else { return }
        await schedule(progressRecords: progressRecords)
    }

    static func refreshIfEnabled(in context: ModelContext) async {
        let records = (try? context.fetch(FetchDescriptor<QuestionProgress>())) ?? []
        await refreshIfEnabled(progressRecords: records)
    }

    static func schedule(progressRecords: [QuestionProgress], now: Date = .now) async {
        let center = UNUserNotificationCenter.current()
        center.removePendingNotificationRequests(withIdentifiers: [dailyIdentifier, nextDueIdentifier])

        let dailyContent = UNMutableNotificationContent()
        dailyContent.title = "CruNote"
        dailyContent.body = "期限の来た問題を復習して、学習を続けましょう。"
        dailyContent.sound = .default
        var dailyComponents = DateComponents()
        dailyComponents.hour = 9
        let dailyTrigger = UNCalendarNotificationTrigger(dateMatching: dailyComponents, repeats: true)
        try? await center.add(
            UNNotificationRequest(identifier: dailyIdentifier, content: dailyContent, trigger: dailyTrigger)
        )

        let studied = progressRecords.filter { $0.attemptCount > 0 }
        guard let earliestDue = studied.map(\.dueDate).min() else { return }
        let triggerDate = max(earliestDue, now.addingTimeInterval(5 * 60))
        let dueByThen = studied.count(where: { $0.dueDate <= triggerDate })
        let dueContent = UNMutableNotificationContent()
        dueContent.title = "復習期限です"
        dueContent.body = "WSETの復習問題が\(dueByThen)問あります。"
        dueContent.sound = .default
        let components = Calendar.current.dateComponents(
            [.year, .month, .day, .hour, .minute],
            from: triggerDate
        )
        let dueTrigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: false)
        try? await center.add(
            UNNotificationRequest(identifier: nextDueIdentifier, content: dueContent, trigger: dueTrigger)
        )
    }
}

enum ReviewNotificationError: LocalizedError {
    case permissionDenied

    var errorDescription: String? {
        "CruNoteの通知が無効です。復習通知を受け取るにはiOSの設定で通知を許可してください。"
    }
}
