# CsharpApp — RealtimeTicker (WPF sample)

A learning-oriented WPF app that exercises the core of the framework in one
place: XAML layout, data binding, MVVM, `INotifyPropertyChanged`,
`ObservableCollection`, `ICommand`, value converters, `DispatcherTimer`-driven
live updates, and custom drawing on a `Canvas`.

It shows a live-updating price ticker for 5 hard-coded instruments; selecting a
row draws that instrument's recent history as a sparkline. Prices come from a
GBM random walk generated in-process — **fully offline, no APIs, and no runtime
NuGet dependencies** (test-only packages aside).

Design: [`docs/superpowers/specs/2026-07-15-realtime-ticker-design.md`](docs/superpowers/specs/2026-07-15-realtime-ticker-design.md).

## Requirements

- Windows .NET SDK 9 (`net9.0-windows`). This repo lives on WSL, so build with
  the Windows `dotnet.exe` — the window opens on the Windows side.

## Build / test / run

From this directory (`CsharpApp`):

```bash
DOTNET="/mnt/c/Program Files/dotnet/dotnet.exe"
"$DOTNET" test CsharpApp.Tests/CsharpApp.Tests.csproj   # xUnit tests
"$DOTNET" run --project CsharpApp.csproj                # launch the app
```

Zero discovered tests counts as a failure even when the command exits 0 — check
the discovered-test count, not just the exit code.

## Layout

```
CsharpApp/
├── Models/                  # UI-free, unit-tested
│   ├── GbmPriceEngine.cs    # GBM step from an injected Random (Box-Muller)
│   ├── PriceHistoryBuffer.cs# fixed-capacity observable ring buffer
│   └── Instrument.cs        # symbol, price, previous price, history
├── ViewModels/
│   ├── ViewModelBase.cs     # INotifyPropertyChanged
│   ├── RelayCommand.cs      # hand-rolled ICommand
│   ├── PriceDirection.cs    # Up / Down / Unchanged UI state
│   ├── TickerViewModel.cs   # one row: price, change %, direction
│   └── MainViewModel.cs     # instrument list, selection, start/pause, timer
├── Views/
│   ├── SparklineControl.cs  # Canvas + Polyline chart, redraws on resize
│   └── PriceFlashBehavior.cs# flash-on-change attached behavior
├── Converters/              # PriceDirection → Brush
└── CsharpApp.Tests/         # xUnit (models, view models, view integration)
```

## Notes

- The **model layer never references `System.Windows`**, which is what makes it
  testable; keep it that way when adding features.
- `GbmPriceEngine` takes a `Random` by constructor injection, so tests are
  deterministic. It also rejects non-finite or non-positive candidates and
  returns the previous price instead — floating-point GBM can underflow even
  though mathematical GBM cannot.
- The update interval is adjustable while running (100–1,000 ms, 50 ms steps);
  `MainViewModel` validates the range and retimes the `DispatcherTimer`.
- View tests need an STA thread — see `CsharpApp.Tests/StaTestRunner.cs`.

Sibling sample: [`../csharp_calc/`](../csharp_calc/) (WinForms calculator).
