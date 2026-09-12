param(
    [string]$SourceFile = "data/missing_xi_sources.csv"
)

$ErrorActionPreference = "Stop"
$rows = Import-Csv -LiteralPath $SourceFile
$resolved = @()

foreach ($row in $rows) {
    if ($row.source_url) {
        $resolved += $row
        continue
    }

    $searchText = "site:mackolik.com/mac/ $($row.query) ilk 11"
    $encoded = [uri]::EscapeDataString($searchText)
    $html = & curl.exe -sL "https://html.duckduckgo.com/html/?q=$encoded" -A "Mozilla/5.0"
    if ($LASTEXITCODE -ne 0) {
        throw "Arama istegi basarisiz: $($row.key)"
    }
    $joined = $html -join "`n"
    $matches = [regex]::Matches($joined, 'uddg=(?<url>https%3A%2F%2Fwww\.mackolik\.com%2Fmac%2F[^&"]+)')
    $urls = @($matches | ForEach-Object {
        [uri]::UnescapeDataString($_.Groups['url'].Value).Replace('&amp;', '&')
    } | Select-Object -Unique)
    if (-not $urls) {
        Write-Warning "Kaynak bulunamadi: $($row.key) - $($row.query)"
        $resolved += $row
        continue
    }

    $row | Add-Member -NotePropertyName source_url -NotePropertyValue $urls[0] -Force
    $resolved += $row
    Write-Host "OK $($row.key) $($urls[0])"
    Start-Sleep -Milliseconds 350
}

$tempFile = "$SourceFile.tmp"
$resolved | Export-Csv -LiteralPath $tempFile -NoTypeInformation -Encoding utf8
Move-Item -LiteralPath $tempFile -Destination $SourceFile -Force

$missing = @($resolved | Where-Object { -not $_.source_url })
Write-Host "Resolved=$($resolved.Count - $missing.Count) Missing=$($missing.Count) Total=$($resolved.Count)"
