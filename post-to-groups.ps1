# ScholarScript Guided Group Poster
# Opens each social group in your browser with the promo post already in your
# clipboard - you just press Ctrl+V and click Post.
#
# EDIT THE $groups LIST BELOW: add YOUR Facebook / WhatsApp / Telegram groups.

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$messageFile = "$projectDir\social-posts\group-post-current.md"

# ─── TARGET GROUPS (edit with your own groups) ───────────────────────
$groups = @(
    @{ Name = "Reddit - r/UGCNet";                Url = "https://www.reddit.com/r/UGCNet/" },
    @{ Name = "Reddit - r/Indian_Academia";       Url = "https://www.reddit.com/r/Indian_Academia/" },
    @{ Name = "Reddit - r/ELATeachers";          Url = "https://www.reddit.com/r/ELATeachers/" },
    @{ Name = "Reddit - r/englishliterature";     Url = "https://www.reddit.com/r/englishliterature/" },
    @{ Name = "Reddit - r/literature";           Url = "https://www.reddit.com/r/literature/" }
    # Add your own groups like this:
    # @{ Name = "Facebook - WBSU English Students"; Url = "https://www.facebook.com/groups/YOUR_GROUP_ID" },
    # @{ Name = "Telegram - English Literature";   Url = "https://t.me/YOUR_GROUP" },
    # @{ Name = "WhatsApp - BA English Semester 7"; Url = "https://chat.whatsapp.com/YOUR_INVITE" },
)

if (-not (Test-Path $messageFile)) {
    Write-Host "Message file not found: $messageFile" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}
$message = Get-Content $messageFile -Raw

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Guided Group Poster" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "For each group: the post is copied to your clipboard and the group"
Write-Host "opens in your browser. Press Ctrl+V, then click Post."
Write-Host ""
Write-Host "Commands at the prompt:  Enter = next group  S = skip  Q = quit"
Write-Host ""
Write-Host "Groups to post to: $($groups.Count)" -ForegroundColor Cyan
Write-Host ""

foreach ($g in $groups) {
    Set-Clipboard -Value $message
    Write-Host ">> $($g.Name)" -ForegroundColor Yellow
    Write-Host "   $($g.Url)" -ForegroundColor DarkCyan
    Start-Process $g.Url
    Start-Sleep -Seconds 2
    $answer = Read-Host "   Posted? Enter=next, S=skip, Q=quit"
    if ($answer -match '^[Qq]') { break }
    if ($answer -match '^[Ss]') { continue }
    Write-Host ""
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Posting session done!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Read-Host "Press Enter to close"
