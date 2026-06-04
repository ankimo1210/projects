# csharp_calc — WinForms Calculator (sample)

A minimal four-function calculator in C# / .NET 9 WinForms. The arithmetic lives
in `Calculator/CalculatorEngine.cs` (no UI dependency, unit-tested);
`Calculator/MainForm.cs` is a thin UI layer.

## Requirements

- Windows .NET SDK 9 (this repo lives on WSL; build with the Windows `dotnet.exe`).

## Build / test / run

From this directory (`csharp_calc`):

```bash
DOTNET="/mnt/c/Program Files/dotnet/dotnet.exe"
"$DOTNET" test Calculator.sln                 # run unit tests
"$DOTNET" run --project Calculator            # launch the app (window opens on Windows)
```

## Layout

- `Calculator/CalculatorEngine.cs` — immediate-execution calculator state machine
- `Calculator/MainForm.cs` — button grid + display, forwards clicks to the engine
- `Calculator.Tests/` — xUnit tests for the engine
