param(
    [ValidateSet('Forward', 'Undo')][string]$Direction = 'Forward',
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\')
$manifestPath = Join-Path $projectRoot 'logs\reorganization-2026-10-02.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.ProjectRoot -ne $projectRoot) { throw 'Manifest project root does not match this checkout.' }

function Resolve-ProjectPath([string]$relative) {
    if ([IO.Path]::IsPathRooted($relative)) { throw "Expected a relative path: $relative" }
    $absolute = [IO.Path]::GetFullPath((Join-Path $projectRoot $relative))
    if (-not $absolute.StartsWith($projectRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside the project: $relative"
    }
    return $absolute
}

function Get-ExpectedTicks($value) {
    # Recent PowerShell versions deserialize ISO dates directly to DateTime.
    $date = if ($value -is [datetime]) { $value } else { [datetime]::Parse($value) }
    return $date.ToUniversalTime().Ticks
}

$destinations = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$operations = @(foreach ($entry in $manifest.Entries) {
    $from = Resolve-ProjectPath $(if ($Direction -eq 'Forward') { $entry.Source } else { $entry.Destination })
    $to = Resolve-ProjectPath $(if ($Direction -eq 'Forward') { $entry.Destination } else { $entry.Source })
    if (-not $destinations.Add($to)) { throw "Duplicate destination: $to" }
    $fromExists = Test-Path -LiteralPath $from
    $toExists = Test-Path -LiteralPath $to
    if ($fromExists -and $toExists) { throw "Both paths exist; refusing to overwrite: $from -> $to" }
    if (-not $fromExists -and -not $toExists) { throw "File is missing at both paths: $from -> $to" }
    $currentPath = if ($fromExists) { $from } else { $to }
    $current = Get-Item -LiteralPath $currentPath
    if ($current.PSIsContainer -or $current.Length -ne $entry.Bytes -or
        $current.LastWriteTimeUtc.Ticks -ne (Get-ExpectedTicks $entry.LastWriteUtc)) {
        throw "File metadata changed since inventory: $currentPath"
    }
    [pscustomobject]@{ Entry=$entry; From=$from; To=$to; Pending=$fromExists }
})

if (-not $Apply) {
    $operations | Select-Object From, To, Pending
    Write-Output 'Preview only. Pass -Apply to perform these moves.'
    return
}

$moved = 0
foreach ($operation in $operations) {
    if (-not $operation.Pending) { continue }
    $parent = Split-Path -Parent $operation.To
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    # File.Move refuses to overwrite an existing destination.
    [IO.File]::Move($operation.From, $operation.To)
    $moved++
}

$verifiedBytes = [long]0
foreach ($operation in $operations) {
    $file = Get-Item -LiteralPath $operation.To
    if ($file.Length -ne $operation.Entry.Bytes -or
        $file.LastWriteTimeUtc.Ticks -ne (Get-ExpectedTicks $operation.Entry.LastWriteUtc) -or
        (Test-Path -LiteralPath $operation.From)) {
        throw "Post-move verification failed: $($operation.To)"
    }
    $verifiedBytes += $file.Length
}
if ($operations.Count -ne $manifest.OriginalFiles -or $verifiedBytes -ne $manifest.OriginalBytes) {
    throw 'Verified totals do not match the original inventory.'
}

$removedEmptyFolders = @()
if ($Direction -eq 'Forward') {
    $obsolete = @('data\crop', 'data\orginal', 'auto_trees', 'leftover', 'propagated_tree',
        'raycloud\35x35', 'raycloud\55x55', 'raycloud', 'rct_output', 'rct_unassigned', 'script')
    foreach ($relative in $obsolete) {
        $folder = Resolve-ProjectPath $relative
        if (Test-Path -LiteralPath $folder -PathType Container) {
            if (@(Get-ChildItem -LiteralPath $folder -Force).Count -eq 0) {
                # Nonrecursive removal: only the explicitly listed, verified empty folder.
                Remove-Item -LiteralPath $folder
                $removedEmptyFolders += $relative
            }
        }
    }
} else {
    foreach ($relative in @('data\crop', 'data\orginal', 'auto_trees', 'leftover', 'propagated_tree',
        'raycloud\35x35', 'raycloud\55x55', 'rct_output', 'rct_unassigned', 'script')) {
        $folder = Resolve-ProjectPath $relative
        if (-not (Test-Path -LiteralPath $folder)) { New-Item -ItemType Directory -Path $folder -Force | Out-Null }
    }
}

[pscustomobject]@{
    Direction = $Direction
    MovedThisRun = $moved
    VerifiedOriginalFiles = $operations.Count
    VerifiedOriginalBytes = $verifiedBytes
    RemovedEmptyFolders = $removedEmptyFolders
} | ConvertTo-Json -Depth 3
