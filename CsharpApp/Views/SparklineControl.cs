using System.Collections.Specialized;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;

namespace CsharpApp.Views;

/// <summary>
/// A lightweight resize-aware sparkline built from a Canvas and Polyline.
/// </summary>
public sealed class SparklineControl : Canvas
{
    private const double ChartPadding = 8.0;
    private const double DotSize = 6.0;

    public static readonly DependencyProperty ValuesProperty =
        DependencyProperty.Register(
            nameof(Values),
            typeof(IReadOnlyList<double>),
            typeof(SparklineControl),
            new FrameworkPropertyMetadata(null, OnValuesChanged));

    public static readonly DependencyProperty StrokeProperty =
        DependencyProperty.Register(
            nameof(Stroke),
            typeof(Brush),
            typeof(SparklineControl),
            new FrameworkPropertyMetadata(Brushes.RoyalBlue, OnStrokeChanged));

    public static readonly DependencyProperty LineThicknessProperty =
        DependencyProperty.Register(
            nameof(LineThickness),
            typeof(double),
            typeof(SparklineControl),
            new FrameworkPropertyMetadata(2.0, OnLineThicknessChanged),
            value => value is double thickness
                && double.IsFinite(thickness)
                && thickness > 0);

    private readonly Ellipse _singlePoint;
    private readonly Polyline _polyline;
    private bool _isSubscribed;

    public SparklineControl()
    {
        Background = Brushes.Transparent;
        ClipToBounds = true;

        _polyline = new Polyline
        {
            Stroke = Stroke,
            StrokeThickness = LineThickness,
            StrokeLineJoin = PenLineJoin.Round,
            SnapsToDevicePixels = true,
        };
        _singlePoint = new Ellipse
        {
            Width = DotSize,
            Height = DotSize,
            Fill = Stroke,
            Visibility = Visibility.Collapsed,
        };

        Children.Add(_polyline);
        Children.Add(_singlePoint);

        Loaded += OnLoaded;
        Unloaded += OnUnloaded;
        SizeChanged += OnSizeChanged;
    }

    public IReadOnlyList<double>? Values
    {
        get => (IReadOnlyList<double>?)GetValue(ValuesProperty);
        set => SetValue(ValuesProperty, value);
    }

    public Brush Stroke
    {
        get => (Brush)GetValue(StrokeProperty);
        set => SetValue(StrokeProperty, value);
    }

    public double LineThickness
    {
        get => (double)GetValue(LineThicknessProperty);
        set => SetValue(LineThicknessProperty, value);
    }

    private static void OnValuesChanged(
        DependencyObject dependencyObject,
        DependencyPropertyChangedEventArgs eventArgs)
    {
        var control = (SparklineControl)dependencyObject;

        if (control._isSubscribed)
        {
            control.Unsubscribe(eventArgs.OldValue as IReadOnlyList<double>);
            control.Subscribe(eventArgs.NewValue as IReadOnlyList<double>);
        }

        control.Redraw();
    }

    private static void OnStrokeChanged(
        DependencyObject dependencyObject,
        DependencyPropertyChangedEventArgs eventArgs)
    {
        var control = (SparklineControl)dependencyObject;
        var brush = (Brush)eventArgs.NewValue;
        control._polyline.Stroke = brush;
        control._singlePoint.Fill = brush;
    }

    private static void OnLineThicknessChanged(
        DependencyObject dependencyObject,
        DependencyPropertyChangedEventArgs eventArgs)
    {
        var control = (SparklineControl)dependencyObject;
        control._polyline.StrokeThickness = (double)eventArgs.NewValue;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (!_isSubscribed)
        {
            _isSubscribed = true;
            Subscribe(Values);
        }

        Redraw();
    }

    private void OnUnloaded(object sender, RoutedEventArgs e)
    {
        if (!_isSubscribed)
        {
            return;
        }

        Unsubscribe(Values);
        _isSubscribed = false;
    }

    private void OnSizeChanged(object sender, SizeChangedEventArgs e) => Redraw();

    private void OnCollectionChanged(object? sender, NotifyCollectionChangedEventArgs e)
    {
        Redraw();
    }

    private void Subscribe(IReadOnlyList<double>? source)
    {
        if (source is INotifyCollectionChanged observable)
        {
            observable.CollectionChanged += OnCollectionChanged;
        }
    }

    private void Unsubscribe(IReadOnlyList<double>? source)
    {
        if (source is INotifyCollectionChanged observable)
        {
            observable.CollectionChanged -= OnCollectionChanged;
        }
    }

    private void Redraw()
    {
        _polyline.Points.Clear();
        _singlePoint.Visibility = Visibility.Collapsed;

        var width = ActualWidth;
        var height = ActualHeight;
        if (!double.IsFinite(width)
            || !double.IsFinite(height)
            || width <= 0
            || height <= 0
            || Values is null)
        {
            return;
        }

        var values = Values.Where(double.IsFinite).ToArray();
        if (values.Length == 0)
        {
            return;
        }

        if (values.Length == 1)
        {
            SetLeft(_singlePoint, (width - DotSize) / 2.0);
            SetTop(_singlePoint, (height - DotSize) / 2.0);
            _singlePoint.Visibility = Visibility.Visible;
            return;
        }

        var innerWidth = width - 2.0 * ChartPadding;
        var innerHeight = height - 2.0 * ChartPadding;
        if (innerWidth <= 0 || innerHeight <= 0)
        {
            return;
        }

        var minimum = values.Min();
        var maximum = values.Max();
        var isFlat = maximum.Equals(minimum);
        var points = new PointCollection(values.Length);

        for (var index = 0; index < values.Length; index++)
        {
            var x = ChartPadding + innerWidth * index / (values.Length - 1.0);
            var y = isFlat
                ? height / 2.0
                : ChartPadding + (maximum - values[index]) / (maximum - minimum) * innerHeight;
            points.Add(new Point(x, y));
        }

        _polyline.Points = points;
    }
}
