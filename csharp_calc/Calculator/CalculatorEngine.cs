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
