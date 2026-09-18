import SwiftUI
import UIKit

enum AppTheme {
    static var wine: Color { adaptive(light: (0.43, 0.12, 0.19), dark: (0.83, 0.43, 0.52)) }
    static var wineSoft: Color { adaptive(light: (0.96, 0.90, 0.91), dark: (0.25, 0.14, 0.18)) }
    /// High contrast fill for controls that use white labels in both appearances.
    static var wineAction: Color { adaptive(light: (0.43, 0.12, 0.19), dark: (0.50, 0.16, 0.25)) }
    static var forest: Color { adaptive(light: (0.17, 0.33, 0.26), dark: (0.55, 0.76, 0.63)) }
    static var forestSoft: Color { adaptive(light: (0.88, 0.93, 0.88), dark: (0.13, 0.23, 0.18)) }
    static var paper: Color { adaptive(light: (0.97, 0.96, 0.92), dark: (0.08, 0.10, 0.09)) }
    static var surface: Color { Color(uiColor: .secondarySystemGroupedBackground) }

    private static func adaptive(light: (CGFloat, CGFloat, CGFloat), dark: (CGFloat, CGFloat, CGFloat)) -> Color {
        Color(uiColor: UIColor { traits in
            let value = traits.userInterfaceStyle == .dark ? dark : light
            return UIColor(red: value.0, green: value.1, blue: value.2, alpha: 1)
        })
    }

    /// Semantic colours are shared so status meaning remains consistent across screens.
    static var success: Color { Color(uiColor: .systemGreen) }
    static var warning: Color { Color(uiColor: .systemOrange) }
    static var error: Color { Color(uiColor: .systemRed) }

    /// Ordered, colour-blind-conscious series colours for charts with several dimensions.
    static let chartPalette: [Color] = [
        wine,
        Color(red: 0.08, green: 0.42, blue: 0.58),
        Color(red: 0.75, green: 0.45, blue: 0.06),
        Color(red: 0.33, green: 0.52, blue: 0.24),
        Color(red: 0.45, green: 0.32, blue: 0.67),
    ]
}
