# fix_longpath.ps1
# Bật Long Path Support trên Windows (cần chạy với quyền Administrator)
# Sau khi chạy script này, pip install wagtail sẽ hoạt động bình thường

Write-Host "==> Enabling Windows Long Path Support..." -ForegroundColor Cyan

$key = "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem"
$name = "LongPathsEnabled"

try {
    Set-ItemProperty -Path $key -Name $name -Value 1 -Type DWord
    $val = Get-ItemProperty -Path $key -Name $name
    if ($val.LongPathsEnabled -eq 1) {
        Write-Host "✅ Long Path Support đã được bật thành công!" -ForegroundColor Green
        Write-Host "   Vui lòng KHỞI ĐỘNG LẠI terminal (không cần restart máy)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Lỗi: Cần chạy PowerShell với quyền Administrator" -ForegroundColor Red
    Write-Host "   Right-click PowerShell → 'Run as Administrator' → chạy lại script này" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==> Sau khi bật Long Path, chạy các lệnh sau:" -ForegroundColor Cyan
Write-Host "   pip install wagtail==6.1.3 --force-reinstall" -ForegroundColor White
Write-Host "   python manage.py migrate" -ForegroundColor White
Write-Host "   python manage.py generate_mock_data" -ForegroundColor White
Write-Host "   python manage.py runserver" -ForegroundColor White
