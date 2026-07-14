#pragma once
// Stability probe: sort (key, original index) records where ordering sees the
// key only; a sort is observed stable iff every equal-key run keeps ascending
// original indices.
#include <cstdint>
#include <stdexcept>
#include <vector>

#include "lab/datagen.hpp"

namespace lab {

struct KeyIdx {
    int key = 0;
    int idx = 0;
    friend bool operator<(const KeyIdx& a, const KeyIdx& b) { return a.key < b.key; }
    friend bool operator==(const KeyIdx& a, const KeyIdx& b) { return a.key == b.key; }
};

struct KeyIdxKey {
    std::uint64_t operator()(const KeyIdx& e) const {
        if (e.key < 0) throw std::invalid_argument("KeyIdxKey: negative key");
        return static_cast<std::uint64_t>(e.key);
    }
};

// fn: void(std::vector<KeyIdx>&) — must sort by key.
template <class SortFn>
bool observed_stable(SortFn fn, std::size_t n = 4096, std::uint32_t seed = 7) {
    const auto keys = generate(Dist::few_unique, n, seed);
    std::vector<KeyIdx> v(n);
    for (std::size_t i = 0; i < n; ++i) v[i] = KeyIdx{keys[i], static_cast<int>(i)};
    fn(v);
    for (std::size_t i = 1; i < n; ++i) {
        if (v[i - 1].key > v[i].key) return false;  // not even sorted
        if (v[i - 1].key == v[i].key && v[i - 1].idx > v[i].idx) return false;
    }
    return true;
}

}  // namespace lab
