$exclude = @('node_modules', '__pycache__', '.venv', '.vscode', 'audio_cache', 'runlogs', '.git', '.orb-assistant', 'Code Cache', 'GPUCache', 'DawnCache', 'Local Storage', 'Network', 'Session Storage', 'blob_storage', 'leveldb', 'tests', 'results', 'test_results')
$includeExt = @('.py', '.js', '.json', '.md', '.txt', '.html', '.css')
function Get-Tree {
    param($path, $prefix = "")
    $items = Get-ChildItem $path | Where-Object {
        ($exclude -notcontains $_.Name) -and
        ($_.PSIsContainer -or ($includeExt -contains $_.Extension -and $_.Name -notmatch '^[a-f0-9]{64}\.json$' -and $_.Name -notmatch '^test_'))
    }
    for ($i = 0; $i -lt $items.Count; $i++) {
        $item = $items[$i]
        $isLast = $i -eq ($items.Count - 1)
        $symbol = if ($isLast) { "└── " } else { "├── " }
        Write-Output "$prefix$symbol$($item.Name)"
        if ($item.PSIsContainer) {
            $newPrefix = if ($isLast) { "$prefix    " } else { "$prefix│   " }
            Get-Tree $item.FullName $newPrefix
        }
    }
}
Get-Tree . > folder_tree.txt