#pragma once
// Deterministic text and pattern generators for the search benchmarks.
// Four text kinds: dna (sigma=4), ascii (printable), english-like (word
// stream), periodic (all 'a' -- with pattern a^(m-1) b this is the classic
// naive / Rabin-Karp worst case and KMP's home turf).
#include <array>
#include <cstddef>
#include <cstdint>
#include <random>
#include <stdexcept>
#include <string>
#include <string_view>

namespace lab {

enum class Text { dna, ascii_random, english_like, periodic };

inline constexpr std::array<Text, 4> all_texts() {
    return {Text::dna, Text::ascii_random, Text::english_like, Text::periodic};
}

inline std::string_view text_name(Text t) {
    switch (t) {
        case Text::dna: return "dna";
        case Text::ascii_random: return "ascii";
        case Text::english_like: return "english";
        case Text::periodic: return "periodic";
    }
    return "unknown";
}

inline constexpr std::array<std::string_view, 32> kEnglishWords = {
    "the",  "of",   "and",  "to",   "in",   "is",   "that", "it",
    "was",  "for",  "on",   "are",  "with", "as",   "at",   "be",
    "this", "have", "from", "or",   "one",  "had",  "by",   "word",
    "but",  "not",  "what", "all",  "were", "when", "we",   "there"};

inline std::string generate_text(Text t, std::size_t n, std::uint32_t seed) {
    std::string s;
    s.reserve(n);
    std::mt19937 rng(seed);
    switch (t) {
        case Text::dna: {
            constexpr std::string_view abc = "ACGT";
            std::uniform_int_distribution<std::size_t> u(0, abc.size() - 1);
            for (std::size_t i = 0; i < n; ++i) s.push_back(abc[u(rng)]);
            break;
        }
        case Text::ascii_random: {
            std::uniform_int_distribution<int> u(32, 126);
            for (std::size_t i = 0; i < n; ++i) s.push_back(static_cast<char>(u(rng)));
            break;
        }
        case Text::english_like: {
            std::uniform_int_distribution<std::size_t> u(0, kEnglishWords.size() - 1);
            while (s.size() < n) {
                s.append(kEnglishWords[u(rng)]);
                s.push_back(' ');
            }
            s.resize(n);
            break;
        }
        case Text::periodic:
            s.assign(n, 'a');
            break;
    }
    return s;
}

inline std::string pattern_for(Text t, const std::string& text, std::size_t m,
                               std::uint32_t seed) {
    if (m == 0) return {};
    if (t == Text::periodic) {
        std::string p(m, 'a');
        p.back() = 'b';  // never occurs in the all-'a' text
        return p;
    }
    if (m > text.size()) throw std::invalid_argument("pattern_for: m > text size");
    std::mt19937 rng(seed ^ 0x9e3779b9u);  // decouple from the text's stream
    std::uniform_int_distribution<std::size_t> pos(0, text.size() - m);
    return text.substr(pos(rng), m);
}

}  // namespace lab
