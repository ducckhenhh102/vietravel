@echo off
REM start_dev.bat — Khoi dong web ban ve du lich (chay sau khi da pip install)
REM Yeu cau: Python 3.11+, da cai xong requirements
if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo.
echo  ==========================================
echo   VietTravel Dev Server Startup Script
echo  ==========================================
echo.

cd /d "%~dp0"

echo [1/4] Chay database migrations...
%PYTHON% manage.py migrate
if %ERRORLEVEL% NEQ 0 (
    echo    LOI: migrate that bai. Kiem tra lai cai dat.
    pause
    exit /b 1
)

echo.
echo [2/4] Collect static files...
%PYTHON% manage.py collectstatic --noinput --clear

echo.
echo [3/4] Tao superuser admin (neu chua co)...
%PYTHON% manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@viettravel.vn', 'admin123'); print('Admin: admin / admin123')"

echo.
echo [4/4] Sinh du lieu mau (500 KH, 2000 don dat)...
%PYTHON% manage.py generate_mock_data --customers 100 --bookings 500
echo    (Chay generate_mock_data day du: %PYTHON% manage.py generate_mock_data --customers 500 --bookings 2000)

echo.
echo  ==========================================
echo   SERVER DANG CHAY TAI: http://localhost:8000
echo   Wagtail Admin    : http://localhost:8000/admin/
echo   API Stats        : http://localhost:8000/api/stats/
echo   Dang nhap Admin  : admin / admin123
echo  ==========================================
echo.

%PYTHON% manage.py runserver 0.0.0.0:8000
