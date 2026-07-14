#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"

TEST_CASE("smoke: doctest runs under sanitizers") {
    CHECK(1 + 1 == 2);
}
