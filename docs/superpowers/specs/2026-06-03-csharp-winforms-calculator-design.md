# C# WinForms Calculator — Sample App Design

**Date:** 2026-06-03
**Status:** Approved (design phase)

## Goal

A small, runnable C# desktop sample app: a basic four-function calculator built
with WinForms. The point is a clean, idiomatic sample that demonstrates
separating UI from logic — not a feature-rich calculator.

## Environment

- No .NET on the Linux/WSL side.
- Windows side has .NET SDK 9.0.203 with `Microsoft.WindowsDesktop.App` 9.0.4,
  so WinForms builds and runs there.
- Project lives on the WSL filesystem under `~/projects/csharp_calc`; build,
  test, and run via the Windows `dotnet.exe`. The GUI window appears on the
  Windows desktop.

## Architecture

```
csharp_calc/
  Calculator.sln
  Calculator/                     WinForms app  (net9.0-windows, UseWindowsForms)
    Program.cs                    entry point
    MainForm.cs                   UI: button grid + display, calls the engine
    CalculatorEngine.cs           calculation logic — no WinForms dependency
  Calculator.Tests/               xUnit          (net9.0-windows)
    CalculatorEngineTests.cs
```

### CalculatorEngine (logic, testable in isolation)

A classic immediate-execution calculator modeled as a small state machine
(`current operand` / `pending operator` / `stored value`), *not* an expression
parser. Public surface, all returning the string that should be displayed:

- `InputDigit(string digit)` — append a digit (0–9) to the current operand.
- `InputDecimal()` — add a decimal point; ignored if the operand already has one.
- `InputOperator(char op)` — one of `+ - * /`. Applies any pending operation,
  then stores the new pending operator.
- `Equals()` — apply the pending operation and show the result.
- `Clear()` — reset to initial state (display `0`).
- `Display` — current string to show.

Engine references no WinForms types, so it is unit-testable on its own.

### MainForm (UI, kept thin)

- Read-only display (right-aligned `Label` or read-only `TextBox`) across the top.
- Button grid: `7 8 9 ÷`, `4 5 6 ×`, `1 2 3 −`, `0 . = +`, plus a `C` (clear).
- Each button's click handler calls one engine method and writes
  `engine.Display` back to the display control. No arithmetic in the UI.

## Scope (YAGNI)

In scope:
- Digits 0–9, decimal point, four operations (+ − × ÷), equals, clear.
- Divide-by-zero → display `Error`, then state resets on next input.
- Prevent a second decimal point in the same operand.

Out of scope (possible later extensions): scientific functions, calculation
history, keyboard input, backspace, sign toggle, memory keys.

## Error Handling

- Division by zero: engine returns `Error`; the next digit/clear starts fresh.
- Invalid/edge sequences (operator pressed first, repeated operators) are
  absorbed by the state machine rather than throwing.

## Testing

xUnit tests on `CalculatorEngine` (logic only — the WinForms UI is not unit
tested). Cases include:

- `2 + 3 =` → `5`
- `5 - 8 =` → `-3`
- `6 * 7 =` → `42`
- `8 / 0 =` → `Error`, and recovery after `Clear`
- decimal: `1 . 5 + 2 . 5 =` → `4`
- double decimal ignored: `1 . . 5` → operand is `1.5`
- chained ops: `2 + 3 * 4 =` → `20` (immediate execution, left to right)
- `Clear` resets to `0`

## Build / Run / Verify

All via the Windows `dotnet.exe` from the project dir on WSL:

- `dotnet.exe test`  — run unit tests (output quoted as evidence).
- `dotnet.exe build` — confirm the app compiles.
- `dotnet.exe run --project Calculator` — launches the window on the Windows
  desktop for visual confirmation.

Verification note: a WinForms GUI cannot be screenshotted from WSL, so final
visual confirmation is done by the user on their Windows desktop. Test output
and build success are reported directly.
