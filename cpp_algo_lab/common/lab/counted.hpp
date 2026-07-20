#pragma once
// Counted<T>: element wrapper that counts comparisons, moves and swaps.
// Feed a std::vector<Counted<int>> through any sort template to measure
// operation counts without touching the algorithm (time runs use plain int).
#include <utility>

namespace lab {

struct OpCounters {
    unsigned long long comparisons = 0;
    unsigned long long moves = 0;  // copy/move construction and assignment
    unsigned long long swaps = 0;  // ADL swap calls
};

template <class T>
class Counted {
public:
    Counted() = default;
    Counted(T v) : value_(std::move(v)) {}  // implicit: allows Counted<int> c = 3

    Counted(const Counted& o) : value_(o.value_) { ++counters().moves; }
    Counted(Counted&& o) noexcept : value_(std::move(o.value_)) { ++counters().moves; }
    Counted& operator=(const Counted& o) {
        value_ = o.value_;
        ++counters().moves;
        return *this;
    }
    Counted& operator=(Counted&& o) noexcept {
        value_ = std::move(o.value_);
        ++counters().moves;
        return *this;
    }

    const T& value() const noexcept { return value_; }

    static OpCounters& counters() {
        thread_local OpCounters c;
        return c;
    }
    static void reset_counters() { counters() = OpCounters{}; }

    friend bool operator<(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return a.value_ < b.value_;
    }
    friend bool operator>(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return b.value_ < a.value_;
    }
    friend bool operator<=(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return !(b.value_ < a.value_);
    }
    friend bool operator>=(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return !(a.value_ < b.value_);
    }
    friend bool operator==(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return a.value_ == b.value_;
    }
    friend bool operator!=(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return !(a.value_ == b.value_);
    }
    friend void swap(Counted& a, Counted& b) noexcept {
        using std::swap;
        swap(a.value_, b.value_);
        ++counters().swaps;
    }

private:
    T value_{};
};

}  // namespace lab
