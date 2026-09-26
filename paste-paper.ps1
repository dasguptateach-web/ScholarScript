# ScholarScript Paste-to-Publish v2.0
# MANUAL STEP: A window opens - YOU paste (Ctrl+V) your manuscript into it and click Publish.
# AUTOMATIC:  Cleaning -> Formatting -> D.Dasgupta watermark -> Build -> Commit & Push -> GitHub Pages deploys.

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

# Auto-detect Python
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) { $pythonExe = "C:\Python310\python.exe" }

$tokenFile = "$projectDir\.github_token"
if (Test-Path $tokenFile) { $env:GITHUB_TOKEN = (Get-Content $tokenFile -Raw).Trim() }

# ===== STEP 1: PASTE WINDOW (the only manual step) ==========================
Write-Host "Opening paste window... paste (Ctrl+V) your manuscript there." -ForegroundColor Cyan

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$script:publishText = $null
$script:form = New-Object System.Windows.Forms.Form
$script:form.Text = "ScholarScript - Paste Your Manuscript"
$script:form.ClientSize = New-Object System.Drawing.Size(880, 600)
$script:form.StartPosition = "CenterScreen"
$script:form.MinimumSize = New-Object System.Drawing.Size(640, 420)

$script:label = New-Object System.Windows.Forms.Label
$script:label.Text = "Step 1 (manual): Paste (Ctrl+V) your manuscript below.`nStep 2 (automatic): Click 'Format & Publish' - cleaning, formatting, D.Dasgupta watermark, build and deploy run by themselves."
$script:label.Location = New-Object System.Drawing.Point(12, 12)
$script:label.Size = New-Object System.Drawing.Size(856, 50)
$script:label.Anchor = "Top, Left, Right"
$script:form.Controls.Add($script:label)

$script:textBox = New-Object System.Windows.Forms.TextBox
$script:textBox.Multiline = $true
$script:textBox.ScrollBars = "Vertical"
$script:textBox.WordWrap = $true
$script:textBox.Font = New-Object System.Drawing.Font("Consolas", 11)
$script:textBox.Location = New-Object System.Drawing.Point(12, 68)
$script:textBox.Size = New-Object System.Drawing.Size(856, 474)
$script:textBox.Anchor = "Top, Bottom, Left, Right"
$script:form.Controls.Add($script:textBox)

$script:hint = New-Object System.Windows.Forms.Label
$script:hint.Text = "Closing this window (or Cancel) publishes nothing."
$script:hint.Location = New-Object System.Drawing.Point(12, 558)
$script:hint.Size = New-Object System.Drawing.Size(520, 30)
$script:hint.Anchor = "Bottom, Left"
$script:form.Controls.Add($script:hint)

$script:btnCancel = New-Object System.Windows.Forms.Button
$script:btnCancel.Text = "Cancel"
$script:btnCancel.Location = New-Object System.Drawing.Point(566, 550)
$script:btnCancel.Size = New-Object System.Drawing.Size(90, 34)
$script:btnCancel.Anchor = "Bottom, Right"
$script:btnCancel.Add_Click({ $script:publishText = $null; $script:form.Close() })
$script:form.Controls.Add($script:btnCancel)

$script:btnPublish = New-Object System.Windows.Forms.Button
$script:btnPublish.Text = "Format & Publish"
$script:btnPublish.Location = New-Object System.Drawing.Point(664, 550)
$script:btnPublish.Size = New-Object System.Drawing.Size(204, 34)
$script:btnPublish.Anchor = "Bottom, Right"
$script:btnPublish.Add_Click({
    if (-not $script:textBox.Text.Trim()) {
        [void][System.Windows.Forms.MessageBox]::Show(
            "The window is empty. Paste (Ctrl+V) your manuscript first.",
            "Nothing to publish",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    $script:publishText = $script:textBox.Text
    $script:form.Close()
})
$script:form.Controls.Add($script:btnPublish)

$script:form.CancelButton = $script:btnCancel
[void]$script:form.ShowDialog()

if (-not $script:publishText) {
    Write-Host "Cancelled - nothing was published." -ForegroundColor Yellow
    exit 0
}

$wordCount = ($script:publishText.Trim() -split '\s+').Count
Write-Host "Manuscript received ($wordCount words) - the rest is automatic." -ForegroundColor Cyan

# ===== STEP 2: SAVE PASTED TEXT ==============================================
$tmp = Join-Path $env:TEMP ("scholarscript-paste-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + ".txt")
[System.IO.File]::WriteAllText($tmp, $script:publishText, (New-Object System.Text.UTF8Encoding($false)))

# ===== STEP 3: PASTE -> CLEAN & FORMAT MARKDOWN ==============================
Write-Host "[1/4] Formatting pasted manuscript..." -ForegroundColor Yellow
& $pythonExe -m scholarscript paste --file "$tmp"
if ($LASTEXITCODE -ne 0) {
    [void][System.Windows.Forms.MessageBox]::Show("Formatting failed. Check the console window for details.", "Publish failed", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
    exit 1
}

# ===== STEP 4: EXTRA FORMATTING PASSES =======================================
Write-Host "[2/4] Fixing tables & MCQ formatting..." -ForegroundColor Yellow
& $pythonExe fix_tables.py 2>&1 | Out-Null
& $pythonExe format_mcqs.py 2>&1 | Out-Null

# ===== STEP 5: BUILD =========================================================
Write-Host "[3/4] Building site..." -ForegroundColor Yellow
& $pythonExe -m scholarscript build
if ($LASTEXITCODE -ne 0) {
    [void][System.Windows.Forms.MessageBox]::Show("Site build failed. Check the console window for details.", "Publish failed", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
    exit 1
}

# ===== STEP 6: COMMIT & PUSH (GitHub Actions auto-deploys) ===================
Write-Host "[4/4] Deploying to GitHub Pages..." -ForegroundColor Yellow
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
if ($env:GITHUB_TOKEN) {
    git remote set-url origin "https://dasguptateach-web:$($env:GITHUB_TOKEN)@github.com/dasguptateach-web/ScholarScript.git" 2>&1 | Out-Null
}
git add -A 2>&1 | Out-Null
$out = git commit -m "Paste-publish $ts" 2>&1
if ($out -match 'nothing to commit|nothing changed') {
    Write-Host "Nothing new to push." -ForegroundColor Yellow
} else {
    $pushed = $false
    for ($attempt = 0; $attempt -lt 3 -and -not $pushed; $attempt++) {
        if ($attempt -gt 0) { Start-Sleep -Seconds 3; Write-Host "  Retry $($attempt+1)..." -ForegroundColor DarkYellow }
        try {
            git fetch origin 2>&1 | Out-Null
            git merge -X ours origin/main --no-edit 2>&1 | Out-Null
            $out = git push origin main 2>&1
            if ($LASTEXITCODE -eq 0) { $pushed = $true }
            elseif ($out -match 'Everything up-to-date') { $pushed = $true }
            elseif ($out -match 'rejected|non-fast-forward') {
                Write-Host "  Behind remote - pulling..." -ForegroundColor DarkYellow
                git pull --no-rebase origin main --no-edit 2>$null
            } else { Write-Host "  PUSH ERROR: $out" -ForegroundColor DarkYellow }
        } catch { Write-Host "  GIT EX: $_" -ForegroundColor DarkYellow }
    }
    if ($env:GITHUB_TOKEN) {
        git remote set-url origin "https://github.com/dasguptateach-web/ScholarScript.git" 2>&1 | Out-Null
    }
    if ($pushed) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  Published!" -ForegroundColor Green
        Write-Host "  https://dasguptateach-web.github.io/ScholarScript/papers/" -ForegroundColor Green
        Write-Host "  (GitHub Pages updates in ~1-2 minutes)" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        [void][System.Windows.Forms.MessageBox]::Show("Published! Your paper is live in ~1-2 minutes at:`nhttps://dasguptateach-web.github.io/ScholarScript/papers/", "Published", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    } else {
        [void][System.Windows.Forms.MessageBox]::Show("Push failed - check internet connection. Details in the console window.", "Publish failed", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
    }
}

Remove-Item $tmp -ErrorAction SilentlyContinue
