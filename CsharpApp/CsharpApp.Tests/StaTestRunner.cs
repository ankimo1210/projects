using System.Threading;
using System.Windows.Threading;

namespace CsharpApp.Tests;

internal static class StaTestRunner
{
    public static async Task RunAsync(Func<Task> action)
    {
        var completion = new TaskCompletionSource(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var thread = new Thread(() =>
        {
            var dispatcher = Dispatcher.CurrentDispatcher;
            SynchronizationContext.SetSynchronizationContext(
                new DispatcherSynchronizationContext(dispatcher));

            dispatcher.BeginInvoke(new Action(async () =>
            {
                try
                {
                    await action();
                    completion.SetResult();
                }
                catch (Exception exception)
                {
                    completion.SetException(exception);
                }
                finally
                {
                    dispatcher.BeginInvokeShutdown(DispatcherPriority.Background);
                }
            }));

            Dispatcher.Run();
        })
        {
            IsBackground = true,
            Name = "CsharpApp.Tests.STA",
        };

        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();

        await completion.Task.WaitAsync(TimeSpan.FromSeconds(8));
    }
}
