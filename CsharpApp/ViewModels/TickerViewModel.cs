using CsharpApp.Models;

namespace CsharpApp.ViewModels;

public sealed class TickerViewModel : ViewModelBase
{
    private readonly Instrument _instrument;

    public TickerViewModel(Instrument instrument)
    {
        _instrument = instrument ?? throw new ArgumentNullException(nameof(instrument));
    }

    public string Symbol => _instrument.Symbol;

    public double Price => _instrument.Price;

    public double PreviousPrice => _instrument.PreviousPrice;

    public double Drift => _instrument.Drift;

    public double Volatility => _instrument.Volatility;

    public IReadOnlyList<double> History => _instrument.History;

    public double ChangePercent =>
        (Price - PreviousPrice) / PreviousPrice * 100.0;

    public string ChangePercentText => $"{ChangePercent:+0.00;-0.00;0.00}%";

    public PriceDirection Direction => Price.CompareTo(PreviousPrice) switch
    {
        > 0 => PriceDirection.Up,
        < 0 => PriceDirection.Down,
        _ => PriceDirection.Unchanged,
    };

    public void UpdatePrice(double price)
    {
        _instrument.UpdatePrice(price);

        OnPropertyChanged(nameof(PreviousPrice));
        OnPropertyChanged(nameof(Price));
        OnPropertyChanged(nameof(ChangePercent));
        OnPropertyChanged(nameof(ChangePercentText));
        OnPropertyChanged(nameof(Direction));
    }
}
