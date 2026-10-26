# Open ITSMe_all163_results.xlsx read-only in Excel and record sheet ranges, row count and sample cell colours.
param([Parameter(Mandatory = $true)][string]$Out)
$x = Join-Path $Out 'ITSMe_all163_results.xlsx'
$report = [ordered]@{ workbook = $x; opened = $false }
try {
    $xl = New-Object -ComObject Excel.Application
    $xl.DisplayAlerts = $false
    $wb = $xl.Workbooks.Open($x, 0, $true)
    $report.opened = $true
    $report.sheets = @($wb.Worksheets | ForEach-Object { "$($_.Name): $($_.UsedRange.Address())" })
    $ws = $wb.Worksheets.Item('All Tree Results')
    $report.tree_rows = $ws.UsedRange.Rows.Count - 1
    $hdr = @{}; for ($c = 1; $c -le $ws.UsedRange.Columns.Count; $c++) { $hdr[$ws.Cells.Item(1, $c).Text] = $c }
    $samples = @()
    foreach ($r in 2, 50, 100, 164) {
        foreach ($name in 'Height status', 'DBH status', 'Crown volume status') {
            $cell = $ws.Cells.Item($r, $hdr[$name])
            $rgb = $cell.Interior.Color; $hex = '{0:X2}{1:X2}{2:X2}' -f ($rgb -band 255), (($rgb -shr 8) -band 255), (($rgb -shr 16) -band 255)
            $samples += "$($ws.Cells.Item($r,1).Text) $name=$($cell.Text) fill=#$hex"
        }
    }
    $report.colour_samples = $samples
    $wb.Close($false); $xl.Quit()
} catch { $report.error = $_.Exception.Message }
$report | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $Out 'logs\excel_open_check.json')
$report | ConvertTo-Json
