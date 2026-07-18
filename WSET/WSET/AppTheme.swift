import SwiftUI

enum AppTheme {
    static let wine = Color(red: 0.43, green: 0.12, blue: 0.19)
    static let wineSoft = Color(red: 0.96, green: 0.90, blue: 0.91)

    /// Semantic colours are shared so status meaning remains consistent across screens.
    static let success = Color(red: 0.08, green: 0.48, blue: 0.25)
    static let warning = Color(red: 0.72, green: 0.43, blue: 0.02)
    static let error = Color(red: 0.72, green: 0.12, blue: 0.16)

    /// Ordered, colour-blind-conscious series colours for charts with several dimensions.
    static let chartPalette: [Color] = [
        wine,
        Color(red: 0.08, green: 0.42, blue: 0.58),
        Color(red: 0.75, green: 0.45, blue: 0.06),
        Color(red: 0.33, green: 0.52, blue: 0.24),
        Color(red: 0.45, green: 0.32, blue: 0.67),
    ]
}
