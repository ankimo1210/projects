#pragma once
// Shared tuning constants for the CPU parallel ladder.
#include <cstddef>

namespace lab {

// Subranges below this size are sorted sequentially: thread-spawn / task
// overhead dominates any parallel win at this scale.
inline constexpr std::ptrdiff_t kParallelSortCutoff = std::ptrdiff_t{1} << 15;

}  // namespace lab
