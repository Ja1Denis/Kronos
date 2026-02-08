$WshShell = New-Object -ComObject WScript.Shell
$ShortcutPath = [System.IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), "Kronos AI Chat.lnk")
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "e:\G\GeminiCLI\ai-test-project\kronos\run_chat.bat"
$Shortcut.WorkingDirectory = "e:\G\GeminiCLI\ai-test-project\kronos"
$Shortcut.WindowStyle = 1
$Shortcut.Description = "Pokreni Kronos AI Chat"
$Shortcut.Save()
Write-Host "✅ Prečaca 'Kronos AI Chat' je kreiran na radnoj površini!"
