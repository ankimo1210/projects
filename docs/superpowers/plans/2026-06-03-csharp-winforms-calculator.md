# C# WinForms Calculator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable WinForms four-function calculator sample that cleanly separates calculation logic (unit-tested) from the UI.

**Architecture:** A `CalculatorEngine` class holds an immediate-execution state machine with no WinForms dependency, so it is unit-testable in isolation. A thin `MainForm` lays out a button grid + display and forwards each click to one engine method, writing the returned string back to the display.

**Tech Stack:** C#, .NET 9 WinForms (`net9.0-windows`), xUnit. Built/run with the **Windows** `dotnet.exe` from the WSL filesystem.

---

## Toolchain Notes (read first)

- There is **no .NET on the Linux side**. Use the Windows SDK:
  `DOTNET="/mnt/c/Program Files/dotnet/dotnet.exe"`
- Run all `dotnet.exe` commands **with the working directory inside the project**
  (`/home/kazumasa/projects/csharp_calc`). When a Windows process is launched from
  a WSL directory, the cwd is auto-translated to `\\wsl.localhost\Ubuntu\...`, so
  `dotnet.exe` operates on the project correctly. Do **not** pass Linux-style path
  arguments (e.g. `/home/...`) to `dotnet.exe` — Windows can't resolve them. Use
  project-relative paths or `wslpath -w` if an absolute path is unavoidable.
- The GUI window opens on the Windows desktop. It cannot be screenshotted from WSL;
  final visual confirmation is the user's.

Set the working directory once (its own command, so no compound-`cd` prompt):
```bash
cd /home/kazumasa/projects/csharp_calc
```

---

## File Structure

```
csharp_calc/
  .gitignore                      bin/ obj/ ignore for the sample
  Calculator.sln
  README.md
  Calculator/                     WinForms app (net9.0-windows, WinExe)
    Calculator.csproj             from `dotnet new winforms` (unchanged)
    Program.cs                    entry point (overwritten)
    MainForm.cs                   UI: display + button grid -> engine
    CalculatorEngine.cs           calculation state machine (no WinForms)
  Calculator.Tests/               xUnit (net9.0-windows)
    Calculator.Tests.csproj       from `dotnet new xunit` (edited: TFM + ref)
    CalculatorEngineTests.cs
```

Each file has one responsibility: `CalculatorEngine` = arithmetic/state, `MainForm` = layout/wiring, `Program` = startup, tests = engine behavior.

---

### Task 1: Scaffold the solution and projects

**Files:**
- Create: `csharp_calc/Calculator.sln`, `csharp_calc/Calculator/*`, `csharp_calc/Calculator.Tests/*`, `csharp_calc/.gitignore`
- Modify: `csharp_calc/Calculator.Tests/Calculator.Tests.csproj`

- [ ] **Step 1: Create the project directory and scaffold**

```bash
DOTNET="/mnt/c/Program Files/dotnet/dotnet.exe"
mkdir -p /home/kazumasa/projects/csharp_calc
cd /home/kazumasa/projects/csharp_calc
"$DOTNET" new winforms -n Calculator -o Calculator
"$DOTNET" new xunit   -n Calculator.Tests -o Calculator.Tests
"$DOTNET" new sln     -n Calculator
"$DOTNET" sln Calculator.sln add Calculator/Calculator.csproj Calculator.Tests/Calculator.Tests.csproj
"$DOTNET" add Calculator.Tests/Calculator.Tests.csproj reference Calculator/Calculator.csproj
```

- [ ] **Step 2: Remove the WinForms template's default form**

```bash
rm -f /home/kazumasa/projects/csharp_calc/Calculator/Form1.cs \
      /home/kazumasa/projects/csharp_calc/Calculator/Form1.Designer.cs \
      /home/kazumasa/projects/csharp_calc/Calculator/Form1.resx
```

- [ ] **Step 3: Retarget the test project to `net9.0-windows`**

The `dotnet new xunit` template targets `net9.0`, which is incompatible with a
`net9.0-windows` project reference. Edit `Calculator.Tests/Calculator.Tests.csproj`
so the `<PropertyGroup>` reads (keep the template's other lines such as
`ImplicitUsings`, `Nullable`, `IsPackable`, `IsTestProject`):

```xml
  <PropertyGroup>
    <TargetFramework>net9.0-windows</TargetFramework>
    <UseWindowsForms>true</UseWindowsForms>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
```

Change only the `TargetFramework` value and add the `UseWindowsForms` line; leave
the package references and `<Using Include="Xunit" />` exactly as generated.

- [ ] **Step 4: Add a project-local `.gitignore`**

Create `csharp_calc/.gitignore` (the root `.gitignore` does not ignore build output):

```gitignore
bin/
obj/
*.user
```

- [ ] **Step 5: Restore + build the scaffold**

```bash
cd /home/kazumasa/projects/csharp_calc
"$DOTNET" build Calculator.sln
```
Expected: `Build succeeded` with 0 errors. (Form1 is gone and Program.cs still
references it, so if this fails on `Form1`, proceed to Task 3 which overwrites
Program.cs — but prefer to do Step 6 first.)

> Note: the template `Program.cs` references `Form1`. To keep this task's build
> green, temporarily it's fine for build to fail here on the missing `Form1`;
> the next step fixes it. If you prefer a green build at every commit, do Task 3
> Step 1 (overwrite Program.cs) before building.

- [ ] **Step 6: Overwrite `Program.cs` so the scaffold builds**

Replace `csharp_calc/Calculator/Program.cs` with:

```csharp
using System;
using System.Windows.Forms;

namespace Calculator;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }
}
```

This references `MainForm`, which does not exist yet, so the app project will not
build until Task 3. That is expected. The **test** project does not depend on
`MainForm`, so engine tests in Task 2 still build and run.

- [ ] **Step 7: Commit**

```bash
cd /home/kazumasa/projects/csharp_calc
git add -A
git commit -m "chore(csharp_calc): scaffold WinForms + xUnit solution"
```

---

### Task 2: CalculatorEngine (TDD)

**Files:**
- Create: `csharp_calc/Calculator/CalculatorEngine.cs`
- Test: `csharp_calc/Calculator.Tests/CalculatorEngineTests.cs`

- [ ] **Step 1: Write the failing tests**

Create `csharp_calc/Calculator.Tests/CalculatorEngineTests.cs`:

```csharp
using Calculator;
using Xunit;

namespace Calculator.Tests;

public class CalculatorEngineTests
{
    [Fact]
    public void Initial_DisplayIsZero()
    {
        Assert.Equal("0", new CalculatorEngine().Display);
    }

    [Fact]
    public void Add_TwoPlusThree_ReturnsFive()
    {
        var e = new CalculatorEngine();
        e.InputDigit("2");
        e.InputOperator('+');
        e.InputDigit("3");
        Assert.Equal("5", e.Evaluate());
    }

    [Fact]
    public void Subtract_FiveMinusEight_ReturnsNegativeThree()
    {
        var e = new CalculatorEngine();
        e.InputDigit("5");
        e.InputOperator('-');
        e.InputDigit("8");
        Assert.Equal("-3", e.Evaluate());
    }

    [Fact]
    public void Multiply_SixTimesSeven_ReturnsFortyTwo()
    {
        var e = new CalculatorEngine();
        e.InputDigit("6");
        e.InputOperator('*');
        e.InputDigit("7");
        Assert.Equal("42", e.Evaluate());
    }

    [Fact]
    public void DivideByZero_ShowsError_AndRecoversAfterClear()
    {
        var e = new CalculatorEngine();
        e.InputDigit("8");
        e.InputOperator('/');
        e.InputDigit("0");
        Assert.Equal("Error", e.Evaluate());

        Assert.Equal("0", e.Clear());
        e.InputDigit("9");
        Assert.Equal("9", e.Display);
    }

    [Fact]
    public void Decimal_OnePointFivePlusTwoPointFive_ReturnsFour()
    {
        var e = new CalculatorEngine();
        e.InputDigit("1");
        e.InputDecimal();
        e.InputDigit("5");
        e.InputOperator('+');
        e.InputDigit("2");
        e.InputDecimal();
        e.InputDigit("5");
        Assert.Equal("4", e.Evaluate());
    }

    [Fact]
    public void Decimal_SecondPointIgnored()
    {
        var e = new CalculatorEngine();
        e.InputDigit("1");
        e.InputDecimal();
        e.InputDecimal();
        e.InputDigit("5");
        Assert.Equal("1.5", e.Display);
    }

    [Fact]
    public void Chained_TwoPlusThreeTimesFour_ReturnsTwenty()
    {
        var e = new CalculatorEngine();
        e.InputDigit("2");
        e.InputOperator('+');
        e.InputDigit("3");
        e.InputOperator('*');
        e.InputDigit("4");
        Assert.Equal("20", e.Evaluate());
    }

    [Fact]
    public void Clear_ResetsToZero()
    {
        var e = new CalculatorEngine();
        e.InputDigit("5");
        e.InputDigit("9");
        Assert.Equal("0", e.Clear());
        Assert.Equal("0", e.Display);
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kazumasa/projects/csharp_calc
"$DOTNET" test Calculator.sln
```
Expected: FAIL — compile error, `CalculatorEngine` does not exist.

- [ ] **Step 3: Implement `CalculatorEngine`**

Create `csharp_calc/Calculator/CalculatorEngine.cs`:

```csharp
using System;
using System.Globalization;

namespace Calculator;

/// <summary>
/// Immediate-execution four-function calculator modeled as a small state
/// machine. Holds no WinForms dependency, so it is unit-testable directly.
/// Every public method returns the string that should be shown on the display.
/// </summary>
public class CalculatorEngine
{
    private string _display = "0";
    private double _stored;
    private char? _pendingOp;
    private bool _startNewOperand = true;
    private bool _error;

    public string Display => _display;

    public string InputDigit(string digit)
    {
        if (_error) ResetState();

        if (_startNewOperand)
        {
            _display = digit;
            _startNewOperand = false;
        }
        else if (_display == "0")
        {
            _display = digit;
        }
        else
        {
            _display += digit;
        }
        return _display;
    }

    public string InputDecimal()
    {
        if (_error) ResetState();

        if (_startNewOperand)
        {
            _display = "0.";
            _startNewOperand = false;
        }
        else if (!_display.Contains('.'))
        {
            _display += ".";
        }
        return _display;
    }

    public string InputOperator(char op)
    {
        if (_error) ResetState();

        double current = Parse(_display);
        if (_pendingOp is null)
        {
            _stored = current;
        }
        else if (!_startNewOperand)
        {
            if (!TryApply(_stored, current, _pendingOp.Value, out double result))
                return SetError();
            _stored = result;
            _display = Format(result);
        }

        _pendingOp = op;
        _startNewOperand = true;
        return _display;
    }

    public string Evaluate()
    {
        if (_error) return _display;
        if (_pendingOp is null) return _display;

        double current = Parse(_display);
        if (!TryApply(_stored, current, _pendingOp.Value, out double result))
            return SetError();

        _display = Format(result);
        _stored = 0;
        _pendingOp = null;
        _startNewOperand = true;
        return _display;
    }

    public string Clear()
    {
        ResetState();
        return _display;
    }

    private void ResetState()
    {
        _display = "0";
        _stored = 0;
        _pendingOp = null;
        _startNewOperand = true;
        _error = false;
    }

    private string SetError()
    {
        _display = "Error";
        _stored = 0;
        _pendingOp = null;
        _startNewOperand = true;
        _error = true;
        return _display;
    }

    private static bool TryApply(double a, double b, char op, out double result)
    {
        switch (op)
        {
            case '+': result = a + b; return true;
            case '-': result = a - b; return true;
            case '*': result = a * b; return true;
            case '/':
                if (b == 0) { result = 0; return false; }
                result = a / b;
                return true;
            default:
                result = 0;
                return false;
        }
    }

    private static double Parse(string s) =>
        double.Parse(s, CultureInfo.InvariantCulture);

    private static string Format(double value)
    {
        double rounded = Math.Round(value, 10);
        return rounded.ToString("0.##########", CultureInfo.InvariantCulture);
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/kazumasa/projects/csharp_calc
"$DOTNET" test Calculator.sln
```
Expected: PASS — all 9 tests pass. Quote the `Passed!` summary line as evidence.

- [ ] **Step 5: Commit**

```bash
cd /home/kazumasa/projects/csharp_calc
git add Calculator/CalculatorEngine.cs Calculator.Tests/CalculatorEngineTests.cs
git commit -m "feat(csharp_calc): calculator engine with unit tests"
```

---

### Task 3: MainForm UI and wiring

**Files:**
- Create: `csharp_calc/Calculator/MainForm.cs`
- (Program.cs was already overwritten in Task 1 Step 6.)

- [ ] **Step 1: Implement `MainForm`**

Create `csharp_calc/Calculator/MainForm.cs`:

```csharp
using System;
using System.Drawing;
using System.Windows.Forms;

namespace Calculator;

public class MainForm : Form
{
    private readonly CalculatorEngine _engine = new();
    private readonly TextBox _display = new();

    public MainForm()
    {
        Text = "Calculator";
        ClientSize = new Size(300, 380);
        FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;

        _display.ReadOnly = true;
        _display.TabStop = false;
        _display.TextAlign = HorizontalAlignment.Right;
        _display.Text = "0";
        _display.Font = new Font("Segoe UI", 24F);
        _display.BorderStyle = BorderStyle.None;
        _display.Dock = DockStyle.Fill;

        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 2,
        };
        root.RowStyles.Add(new RowStyle(SizeType.Absolute, 64F));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
        root.Controls.Add(_display, 0, 0);
        root.Controls.Add(BuildButtonGrid(), 0, 1);

        Controls.Add(root);
    }

    private TableLayoutPanel BuildButtonGrid()
    {
        var grid = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 4,
            RowCount = 5,
        };
        for (int c = 0; c < 4; c++)
            grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25F));
        for (int r = 0; r < 5; r++)
            grid.RowStyles.Add(new RowStyle(SizeType.Percent, 20F));

        string[][] layout =
        {
            new[] { "7", "8", "9", "÷" },
            new[] { "4", "5", "6", "×" },
            new[] { "1", "2", "3", "−" },
            new[] { "0", ".", "=", "+" },
        };

        for (int r = 0; r < layout.Length; r++)
            for (int c = 0; c < layout[r].Length; c++)
                grid.Controls.Add(MakeButton(layout[r][c]), c, r);

        var clear = MakeButton("C");
        grid.Controls.Add(clear, 0, 4);
        grid.SetColumnSpan(clear, 4);

        return grid;
    }

    private Button MakeButton(string text)
    {
        var button = new Button
        {
            Text = text,
            Dock = DockStyle.Fill,
            Font = new Font("Segoe UI", 16F),
            Margin = new Padding(3),
            FlatStyle = FlatStyle.System,
        };
        button.Click += (_, _) => OnButtonClick(text);
        return button;
    }

    private void OnButtonClick(string text)
    {
        _display.Text = text switch
        {
            "C" => _engine.Clear(),
            "=" => _engine.Evaluate(),
            "." => _engine.InputDecimal(),
            "÷" => _engine.InputOperator('/'),
            "×" => _engine.InputOperator('*'),
            "−" => _engine.InputOperator('-'),
            "+" => _engine.InputOperator('+'),
            _ => _engine.InputDigit(text),
        };
    }
}
```

- [ ] **Step 2: Build the whole solution**

```bash
cd /home/kazumasa/projects/csharp_calc
"$DOTNET" build Calculator.sln
```
Expected: `Build succeeded`, 0 errors (both app and tests compile now).

- [ ] **Step 3: Re-run tests (guard against regressions)**

```bash
cd /home/kazumasa/projects/csharp_calc
"$DOTNET" test Calculator.sln
```
Expected: PASS — 9 tests.

- [ ] **Step 4: Commit**

```bash
cd /home/kazumasa/projects/csharp_calc
git add Calculator/MainForm.cs Calculator/Program.cs
git commit -m "feat(csharp_calc): WinForms UI wired to engine"
```

---

### Task 4: README and final verification

**Files:**
- Create: `csharp_calc/README.md`

- [ ] **Step 1: Write the README**

Create `csharp_calc/README.md`:

```markdown
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
```

- [ ] **Step 2: Final test run (capture evidence)**

```bash
cd /home/kazumasa/projects/csharp_calc
"$DOTNET" test Calculator.sln
```
Expected: `Passed!  - Failed: 0, Passed: 9`. Quote this line in the report.

- [ ] **Step 3: Launch the app through its real entry point**

```bash
cd /home/kazumasa/projects/csharp_calc
"$DOTNET" run --project Calculator
```
Expected: a "Calculator" window opens on the Windows desktop. Ask the user to
confirm it renders and that e.g. `7 × 8 =` shows `56`. (A WinForms window cannot
be screenshotted from WSL — visual confirmation is the user's.)

- [ ] **Step 4: Commit**

```bash
cd /home/kazumasa/projects/csharp_calc
git add README.md
git commit -m "docs(csharp_calc): usage README"
```

---

## Self-Review

**Spec coverage:**
- WinForms app + engine + xUnit, 2-project layout → Tasks 1–3. ✓
- Digits / decimal / four ops / equals / clear → engine (Task 2) + UI (Task 3). ✓
- Divide-by-zero → `Error` and recovery → test + `SetError` (Task 2). ✓
- Prevent second decimal point → test + `InputDecimal` (Task 2). ✓
- Chained immediate execution (`2 + 3 * 4 = 20`) → test + `InputOperator` (Task 2). ✓
- Build/run/verify via Windows `dotnet.exe` → toolchain notes + Task 4. ✓

**Naming note:** the spec called the equals method `Equals()`; the plan uses
`Evaluate()` to avoid colliding with `object.Equals`. Behavior is identical;
this is the only intentional deviation.

**Placeholder scan:** none — every code/command step is concrete.

**Type consistency:** engine surface `InputDigit(string)`, `InputDecimal()`,
`InputOperator(char)`, `Evaluate()`, `Clear()`, `Display` is used identically in
tests (Task 2) and `MainForm.OnButtonClick` (Task 3).
```
