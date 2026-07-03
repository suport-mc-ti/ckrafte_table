$backend = Start-Process -FilePath python -ArgumentList "backend/app.py" -PassThru
$frontend = Start-Process -FilePath npm -ArgumentList "--prefix", "frontend", "run", "dev", "--", "--host", "0.0.0.0" -PassThru

Write-Host "Backend PID: $($backend.Id)"
Write-Host "Frontend PID: $($frontend.Id)"
Write-Host "Presiona Ctrl+C en las ventanas abiertas para detener los servicios."