import Foundation

/// SplitMix64-based deterministic random number generator.
///
/// The same seed and input order always produce the same output. This avoids
/// Swift's process-randomized `Hasher` and lets a persisted session reconstruct
/// its question and option order exactly.
public struct SeededRandomNumberGenerator: RandomNumberGenerator, Sendable {
    public private(set) var state: UInt64

    public init(seed: UInt64) {
        state = seed
    }

    public mutating func next() -> UInt64 {
        state &+= 0x9E37_79B9_7F4A_7C15
        var value = state
        value = (value ^ (value >> 30)) &* 0xBF58_476D_1CE4_E5B9
        value = (value ^ (value >> 27)) &* 0x94D0_49BB_1331_11EB
        return value ^ (value >> 31)
    }

    public mutating func nextIndex(upperBound: Int) -> Int {
        precondition(upperBound > 0, "upperBound must be positive")

        let bound = UInt64(upperBound)
        let rejectionThreshold = (UInt64(0) &- bound) % bound
        var candidate = next()

        while candidate < rejectionThreshold {
            candidate = next()
        }

        return Int(candidate % bound)
    }
}

public enum DeterministicShuffle {
    public static func shuffled<Element>(
        _ elements: [Element],
        seed: UInt64
    ) -> [Element] {
        guard elements.count > 1 else { return elements }

        var result = elements
        var generator = SeededRandomNumberGenerator(seed: seed)

        for index in stride(from: result.count - 1, through: 1, by: -1) {
            let swapIndex = generator.nextIndex(upperBound: index + 1)
            if index != swapIndex {
                result.swapAt(index, swapIndex)
            }
        }

        return result
    }

    /// A stable UTF-8 hash; unlike `Hasher`, it is identical across processes.
    public static func stableHash(_ value: String) -> UInt64 {
        var hash: UInt64 = 0xCBF2_9CE4_8422_2325
        for byte in value.utf8 {
            hash ^= UInt64(byte)
            hash &*= 0x0000_0100_0000_01B3
        }
        return hash
    }

    public static func derivedSeed(
        sessionSeed: UInt64,
        identifier: String,
        salt: UInt64 = 0
    ) -> UInt64 {
        sessionSeed ^ stableHash(identifier) ^ salt
    }
}
