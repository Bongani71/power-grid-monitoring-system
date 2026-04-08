$env:PYTHONUTF8=1
cd $PSScriptRoot

echo "⚡ Starting Power Grid Monitoring System..."
echo "Starting Database Seed..."
.\venv_312\Scripts\python.exe seed.py

echo "Training the Forecasting Model once..."
.\venv_312\Scripts\python.exe forecasting\train_model.py

echo "Starting FastAPI Server..."
Start-Process -NoNewWindow -FilePath ".\venv_312\Scripts\uvicorn.exe" -ArgumentList "main:app", "--host", "0.0.0.0", "--port", "8000"

echo "Waiting for API to start..."
Start-Sleep -Seconds 5

echo "Starting Streamlit Dashboard..."
.\venv_312\Scripts\streamlit.exe run dashboard\app.py
