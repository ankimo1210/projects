param(
    [Parameter(Mandatory=$true)][string]$PythonPath,
    [Parameter(Mandatory=$true)][string]$HelperPath,
    [Parameter(Mandatory=$true)][string]$ConfigPath
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Invoke-ApiKeyHelper {
    param(
        [string]$PythonPath, [string]$HelperPath, [string]$ConfigPath,
        [string]$Command, [string]$Payload
    )
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $PythonPath
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.WorkingDirectory = [Environment]::GetFolderPath('UserProfile')
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.StandardInputEncoding = [System.Text.UTF8Encoding]::new($false)
    $start.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $start.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)
    foreach ($argument in @($HelperPath, '--config', $ConfigPath, $Command)) {
        $start.ArgumentList.Add($argument)
    }
    $process = [System.Diagnostics.Process]::Start($start)
    if ($Payload) { $process.StandardInput.Write($Payload) }
    $process.StandardInput.Close()
    $output = $process.StandardOutput.ReadToEnd()
    $errorOutput = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw 'Keys could not be saved. Check the Drive connection and use newly issued keys.'
    }
    $process.Dispose()
    return ($output | ConvertFrom-Json)
}

function New-ApiKeySetupForm {
    $pythonExecutable = $PythonPath
    $helperScript = $HelperPath
    $configurationFile = $ConfigPath
    $invokeHelper = (Get-Item 'Function:Invoke-ApiKeyHelper').ScriptBlock
    $form = [System.Windows.Forms.Form]::new()
    $form.Text = 'API key setup - private Drive storage'
    $form.ClientSize = [System.Drawing.Size]::new(660, 345)
    $form.StartPosition = 'CenterScreen'
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true
    $form.Font = [System.Drawing.Font]::new('Segoe UI', 10)

    $intro = [System.Windows.Forms.Label]::new()
    $intro.Text = 'Paste keys here once. Do not paste them into the chat.'
    $intro.Location = [System.Drawing.Point]::new(18, 15)
    $intro.Size = [System.Drawing.Size]::new(625, 25)
    $form.Controls.Add($intro)

    $note = [System.Windows.Forms.Label]::new()
    $note.Text = 'Blank fields preserve existing keys. Reinfolib requires a NEW key.'
    $note.Location = [System.Drawing.Point]::new(18, 43)
    $note.Size = [System.Drawing.Size]::new(625, 25)
    $form.Controls.Add($note)

    $providers = @('openai', 'anthropic', 'reinfolib')
    $titles = @('OpenAI', 'Anthropic', 'Reinfolib (new key)')
    $boxes = @{}
    for ($index = 0; $index -lt $providers.Length; $index++) {
        $label = [System.Windows.Forms.Label]::new()
        $label.Text = $titles[$index]
        $label.Location = [System.Drawing.Point]::new(18, (86 + 48 * $index))
        $label.Size = [System.Drawing.Size]::new(175, 28)
        $form.Controls.Add($label)

        $box = [System.Windows.Forms.TextBox]::new()
        $box.Location = [System.Drawing.Point]::new(196, (82 + 48 * $index))
        $box.Size = [System.Drawing.Size]::new(440, 28)
        $box.UseSystemPasswordChar = $true
        $box.MaxLength = 4096
        $form.Controls.Add($box)
        $boxes[$providers[$index]] = $box
    }

    $status = [System.Windows.Forms.Label]::new()
    $status.Text = 'Stored only in your private Drive folder and local copy.'
    $status.Location = [System.Drawing.Point]::new(18, 232)
    $status.Size = [System.Drawing.Size]::new(625, 27)
    $form.Controls.Add($status)

    $save = [System.Windows.Forms.Button]::new()
    $save.Text = 'Save to Drive'
    $save.Location = [System.Drawing.Point]::new(395, 280)
    $save.Size = [System.Drawing.Size]::new(130, 36)
    $form.Controls.Add($save)

    $cancel = [System.Windows.Forms.Button]::new()
    $cancel.Text = 'Later'
    $cancel.Location = [System.Drawing.Point]::new(536, 280)
    $cancel.Size = [System.Drawing.Size]::new(100, 36)
    $cancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $form.CancelButton = $cancel
    $form.Controls.Add($cancel)

    $save.Add_Click({
        $save.Enabled = $false
        $payloadObject = @{}
        foreach ($provider in $providers) {
            $payloadObject[$provider] = $boxes[$provider].Text
        }
        try {
            $null = & $invokeHelper -PythonPath $pythonExecutable -HelperPath $helperScript -ConfigPath $configurationFile -Command 'save-json' -Payload (
                $payloadObject | ConvertTo-Json -Compress
            )
            foreach ($box in $boxes.Values) { $box.Clear() }
            $payloadObject.Clear()
            $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
            $form.Close()
        } catch {
            $status.Text = 'Not saved. Check Drive; do not reuse the exposed Reinfolib key.'
            $save.Enabled = $true
        } finally {
            $payloadObject.Clear()
        }
    }.GetNewClosure())
    $form.AcceptButton = $save
    return $form
}

if ($MyInvocation.InvocationName -ne '.') {
    $window = New-ApiKeySetupForm
    [void]$window.ShowDialog()
    $window.Dispose()
}
