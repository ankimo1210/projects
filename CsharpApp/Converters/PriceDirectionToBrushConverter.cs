using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;
using CsharpApp.ViewModels;

namespace CsharpApp.Converters;

[ValueConversion(typeof(PriceDirection), typeof(Brush))]
public sealed class PriceDirectionToBrushConverter : IValueConverter
{
    public object Convert(
        object value,
        Type targetType,
        object parameter,
        CultureInfo culture)
    {
        return value switch
        {
            PriceDirection.Up => Brushes.SeaGreen,
            PriceDirection.Down => Brushes.IndianRed,
            _ => Brushes.SlateGray,
        };
    }

    public object ConvertBack(
        object value,
        Type targetType,
        object parameter,
        CultureInfo culture)
    {
        return DependencyProperty.UnsetValue;
    }
}
