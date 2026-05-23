# 掃描 images/ 下的子資料夾，產生 manifest.json
# 使用方式：在專案根目錄執行 .\build.ps1

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
Write-Host "完成！manifest.json 已更新，包含 $($manifest.Count) 個資料夾。" -ForegroundColor Green
