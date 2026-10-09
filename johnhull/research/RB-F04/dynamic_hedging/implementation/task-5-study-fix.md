# Task5 study review fixes

UTC: 2026-10-09T14:41:44.429567+00:00

**I1–I4 addressed; scoped 59 tests PASS (7.64s), ruff PASS. Independent rereview pending.**

## Changes

- I1: exact linear targets use authoritative evaluate_asian VS and hQ=0, zero block/ratio errors, independent target and band-covariance qualification; nonlinears retain no-fit failure; cash masks ignore only truly unused invalid call price/CF contributions
- I2: dataset model checked against all original training slots, wrong/missing generator attempts retained as failures with original count; tiny completed fixture uses actual Heston/local datasets
- I3: outer/raw seed, universe, training generator, original count, fit/checkpoint identity checked before labeled replay; missing original count also becomes unknown rather than TypeError
- I4: calendar t covariance for t>0/current S0, only unsupported t0 restart can use original first internal midpoint from saved grid; time/source/original support/proxy flags retained

## Binding

- deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_study.py: ff3a72394f86ad572ee2cc62c27fbeb8f047b397bf8e60cf328092464273fb4e
- deep_hedge_price/tests/test_dynamic_hedging_study.py: 9b2dc720aedda15e1f5006cd2f542397fb70af7c411f3ed16e0b2c2f001c9487

## Verification and preserved evidence

- Each original numerical counterexample was added as a regression, observed RED, then verified GREEN. Outer/raw missing original count and common zero-call masks have additional RED records.
- Original independent review and exact reviewed source/tests remain unchanged. The new diff and fixed exact snapshots are saved separately.
- One integration iteration had a covariance-qualification expectation failure after target/band qualification separation; the original failed output remains saved and the final test asserts band unknown with target arithmetic qualified.
- Invalid untraded call mids/CF are exact zero contributions only when raw holdings imply zero cash-event exposure/entitlement. Nonzero liquidation still fails; original unknown quote/CF stays in dataset.
- Full phase/main/pilot qualification, complete source/cost closure, saved semantic replay, independent rereview and final suites remain pending.
