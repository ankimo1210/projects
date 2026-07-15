import Foundation

extension PracticeSeedContent {
    static var allPassages: [PracticePassage] {
        passages + upperIntermediatePassages + advancedPassages
    }

    static func passage(id: String?) -> PracticePassage? {
        guard let id else { return nil }
        return allPassages.first { $0.id == id }
    }
}
