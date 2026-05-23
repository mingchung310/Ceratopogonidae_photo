$manifest = @{}
$imgExts = @('.jpg','.jpeg','.png','.gif','.webp')
if (Test-Path "images") {
    Get-ChildItem "images" -Directory | ForEach-Object {
        $folder = $_.Name
        $files = Get-ChildItem $_.FullName -File |
                 Where-Object { $imgExts -contains $_.Extension.ToLower() } |
                 Sort-Object Name |
                 ForEach-Object { "images/$folder/$($_.Name)" }
        if ($files) { $manifest[$folder] = @($files) }
    }
}
$manifest | ConvertTo-Json -Depth 3 | Out-File "manifest.json" -Encoding utf8
Write-Output "manifest.json updated: $($manifest.Count) folders"