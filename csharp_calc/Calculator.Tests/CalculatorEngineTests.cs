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
