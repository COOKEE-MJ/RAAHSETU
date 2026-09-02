# RaahSetu

RaahSetu is a Flask and SQLite local-transit MVP. It helps passengers search routes, view scheduled departures, submit delay reports, and review reports grouped by delay.

## Features

- Pre-loaded local transport dataset
- Route search by source and destination
- Full timetable for matching routes
- Next expected departure
- Passenger delay reports
- Reports page grouped by delay amount
- Most delayed route summary
- Per-route report counts

## Run Locally

From the project root:

```powershell
C:/Users/mahen/AppData/Local/Programs/Python/Python314/python.exe -m pip install -r requirements.txt
C:/Users/mahen/AppData/Local/Programs/Python/Python314/python.exe create_database.py
C:/Users/mahen/AppData/Local/Programs/Python/Python314/python.exe seed_database.py
C:/Users/mahen/AppData/Local/Programs/Python/Python314/python.exe app.py
```

Open http://127.0.0.1:5000/ in a browser.

## Useful Pages

- `/` - route search and delay report form
- `/reports` - categorized delay reports and most delayed route
- `/health` - backend and database health check
- `/observations` - JSON report data for integrations

## Run Tests

```powershell
C:/Users/mahen/AppData/Local/Programs/Python/Python314/python.exe -m unittest discover -s tests -v
```

The frontend is served from `RaahSetu/templates` and `RaahSetu/static`. The SQLite database is stored at `database/routes.db`.
