# ScholarScript Submissions Cleanup
# Deletes submission files older than 3 days from Desktop folder.
# Runs daily via Windows Scheduled Task.
$submissionsDir = "$env:USERPROFILE\Desktop\ScholarScript Submissions"
$logFile = "$PSScriptRoot\cleanup-submissions.log"
$maxAgeDays = 3

$cutoff = (Get-Date).AddDays(-$maxAgeDays)
$deleted = 0

Get-ChildItem -LiteralPath $submissionsDir -File | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
    try {
        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop
        $deleted++
        $msg = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] DELETED $($_.Name) (age: $([Math]::Round((Get-Date - $_.LastWriteTime).TotalDays, 1)) days)"
        Add-Content -Path $logFile -Value $msg
    } catch {
        $msg = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR deleting $($_.Name): $_"
        Add-Content -Path $logFile -Value $msg
    }
}

if ($deleted -eq 0) {
    $msg = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Cleanup ran — no files older than $maxAgeDays days"
    Add-Content -Path $logFile -Value $msg
}
