using System.ComponentModel;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;
using CsharpApp.ViewModels;

namespace CsharpApp.Views;

/// <summary>
/// Restarts a short row-background animation whenever a bound price changes.
/// This visual-only behavior keeps WPF brushes out of the view models.
/// </summary>
public static class PriceFlashBehavior
{
    public static readonly DependencyProperty IsEnabledProperty =
        DependencyProperty.RegisterAttached(
            "IsEnabled",
            typeof(bool),
            typeof(PriceFlashBehavior),
            new PropertyMetadata(false, OnIsEnabledChanged));

    private static readonly DependencyProperty SubscriptionProperty =
        DependencyProperty.RegisterAttached(
            "Subscription",
            typeof(Subscription),
            typeof(PriceFlashBehavior));

    public static bool GetIsEnabled(DependencyObject element) =>
        (bool)element.GetValue(IsEnabledProperty);

    public static void SetIsEnabled(DependencyObject element, bool value) =>
        element.SetValue(IsEnabledProperty, value);

    private static void OnIsEnabledChanged(
        DependencyObject dependencyObject,
        DependencyPropertyChangedEventArgs eventArgs)
    {
        if (dependencyObject is not DataGridRow row)
        {
            return;
        }

        if ((bool)eventArgs.NewValue)
        {
            var subscription = new Subscription(row);
            row.SetValue(SubscriptionProperty, subscription);
            return;
        }

        if (row.GetValue(SubscriptionProperty) is Subscription existing)
        {
            existing.Dispose();
            row.ClearValue(SubscriptionProperty);
        }
    }

    private sealed class Subscription : IDisposable
    {
        private static readonly TimeSpan FlashDuration = TimeSpan.FromMilliseconds(150);
        private readonly DataGridRow _row;
        private TickerViewModel? _viewModel;
        private long _animationVersion;

        public Subscription(DataGridRow row)
        {
            _row = row;
            _row.Loaded += OnLoaded;
            _row.Unloaded += OnUnloaded;
            _row.DataContextChanged += OnDataContextChanged;

            if (_row.IsLoaded)
            {
                Attach(_row.DataContext as TickerViewModel);
            }
        }

        public void Dispose()
        {
            _row.Loaded -= OnLoaded;
            _row.Unloaded -= OnUnloaded;
            _row.DataContextChanged -= OnDataContextChanged;
            Detach();
            _animationVersion++;
            _row.ClearValue(Control.BackgroundProperty);
        }

        private void OnLoaded(object sender, RoutedEventArgs e)
        {
            Attach(_row.DataContext as TickerViewModel);
        }

        private void OnUnloaded(object sender, RoutedEventArgs e)
        {
            Detach();
            _animationVersion++;
            _row.ClearValue(Control.BackgroundProperty);
        }

        private void OnDataContextChanged(
            object sender,
            DependencyPropertyChangedEventArgs e)
        {
            if (_row.IsLoaded)
            {
                Attach(e.NewValue as TickerViewModel);
            }
        }

        private void Attach(TickerViewModel? viewModel)
        {
            if (ReferenceEquals(_viewModel, viewModel))
            {
                return;
            }

            Detach();
            _viewModel = viewModel;

            if (_viewModel is not null)
            {
                _viewModel.PropertyChanged += OnViewModelPropertyChanged;
            }
        }

        private void Detach()
        {
            if (_viewModel is not null)
            {
                _viewModel.PropertyChanged -= OnViewModelPropertyChanged;
                _viewModel = null;
            }
        }

        private void OnViewModelPropertyChanged(
            object? sender,
            PropertyChangedEventArgs e)
        {
            if (e.PropertyName != nameof(TickerViewModel.Price)
                || sender is not TickerViewModel viewModel
                || viewModel.Direction == PriceDirection.Unchanged)
            {
                return;
            }

            var startColor = viewModel.Direction == PriceDirection.Up
                ? Color.FromRgb(214, 245, 224)
                : Color.FromRgb(253, 222, 222);
            var brush = new SolidColorBrush(startColor);
            var version = ++_animationVersion;

            _row.Background = brush;

            var animation = new ColorAnimation(
                startColor,
                Colors.Transparent,
                new Duration(FlashDuration))
            {
                FillBehavior = FillBehavior.HoldEnd,
            };

            animation.Completed += (_, _) =>
            {
                if (version == _animationVersion)
                {
                    _row.ClearValue(Control.BackgroundProperty);
                }
            };

            brush.BeginAnimation(SolidColorBrush.ColorProperty, animation);
        }
    }
}
