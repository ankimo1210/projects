//
//  HapticsService.swift
//  NeonThread
//

import UIKit

@MainActor
final class HapticsService {
    static let shared = HapticsService()

    private let lightGenerator = UIImpactFeedbackGenerator(style: .light)
    private let mediumGenerator = UIImpactFeedbackGenerator(style: .medium)
    private let heavyGenerator = UIImpactFeedbackGenerator(style: .heavy)
    private let notificationGenerator = UINotificationFeedbackGenerator()

    private var isHapticsEnabled: Bool {
        UserDefaults.standard.object(forKey: "isHapticsEnabled") as? Bool ?? true
    }

    private init() {
        lightGenerator.prepare()
        heavyGenerator.prepare()
    }

    func impact(_ style: UIImpactFeedbackGenerator.FeedbackStyle) {
        guard isHapticsEnabled else { return }
        switch style {
        case .light: lightGenerator.impactOccurred()
        case .medium: mediumGenerator.impactOccurred()
        default: heavyGenerator.impactOccurred()
        }
    }

    func gameOver() {
        guard isHapticsEnabled else { return }
        notificationGenerator.notificationOccurred(.error)
    }
}
