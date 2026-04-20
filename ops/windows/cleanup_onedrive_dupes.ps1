# VUES OneDrive Duplicate Cleanup Script
# Excludes: BaselinePrinter folder
# Action: Moves duplicates to _DUPLICATES_TO_DELETE for review

$ErrorActionPreference = 'Continue'
$onedrive = 'C:\Users\vn59j7j\OneDrive - Walmart Inc'
$exclude = 'BaselinePrinter'
$dupeFolder = Join-Path $onedrive '_DUPLICATES_TO_DELETE'

Write-Host "`n=== OneDrive Duplicate Cleanup ===" -ForegroundColor Cyan
Write-Host "Excluding: $exclude"
Write-Host ""

# Create destination folder
if(!(Test-Path $dupeFolder)) { 
    New-Item -ItemType Directory -Path $dupeFolder -Force | Out-Null 
    Write-Host "Created: $dupeFolder" -ForegroundColor Green
}

Write-Host "Scanning for duplicates (>1MB files)..." -ForegroundColor Yellow

# Find all files >1MB, excluding BaselinePrinter
$files = Get-ChildItem $onedrive -Recurse -File -Force -ErrorAction SilentlyContinue | 
    Where-Object { $_.FullName -notmatch $exclude -and $_.Length -gt 1MB }

Write-Host "Found $($files.Count) files to analyze"

# Group by name to find duplicates
$groups = $files | Group-Object Name | Where-Object { $_.Count -gt 1 }

Write-Host "Found $($groups.Count) sets of duplicate files" -ForegroundColor Yellow
Write-Host ""

$movedCount = 0
$movedSize = 0
$errors = 0

foreach($g in $groups) {
    # Keep the newest file, move older copies
    $sorted = $g.Group | Sort-Object LastWriteTime -Descending
    $keep = $sorted[0]
    $toMove = $sorted | Select-Object -Skip 1
    
    foreach($f in $toMove) {
        # Generate unique destination name
        $destName = $f.Name
        $destPath = Join-Path $dupeFolder $destName
        $i = 1
        while(Test-Path $destPath) {
            $destName = "{0}_{1}{2}" -f $f.BaseName, $i, $f.Extension
            $destPath = Join-Path $dupeFolder $destName
            $i++
        }
        
        try {
            Move-Item -LiteralPath $f.FullName -Destination $destPath -Force -ErrorAction Stop
            $movedCount++
            $movedSize += $f.Length
            
            if($movedCount % 100 -eq 0) {
                Write-Host "  Moved $movedCount files so far..." -ForegroundColor Gray
            }
        } catch {
            $errors++
        }
    }
}

Write-Host ""
Write-Host "=== DONE ===" -ForegroundColor Green
Write-Host "Moved: $movedCount duplicate files" -ForegroundColor Green
Write-Host "Size:  $([math]::Round($movedSize/1GB, 2)) GB" -ForegroundColor Green
if($errors -gt 0) {
    Write-Host "Errors: $errors (files in use or protected)" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Review duplicates here:" -ForegroundColor Cyan
Write-Host "  $dupeFolder"
Write-Host ""
Write-Host "To permanently delete, run:" -ForegroundColor Yellow
Write-Host "  Remove-Item '$dupeFolder' -Recurse -Force"
Write-Host ""
