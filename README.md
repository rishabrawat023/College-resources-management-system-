# Campus Resource Optimizer – Smart College Resource Management System

A responsive Flask web application for managing college spaces, bookings and a FIFO waiting list. It uses **HTML, CSS, JavaScript and Python Flask**. All persistent data is stored in `database.json`; no MySQL or machine learning is used.

## Features

- Dashboard statistics and resource distribution
- CRUD operations for Classrooms, Computer Labs, Seminar Halls and Auditoriums
- Resource fields: capacity, location, smartboard, projector, number of PCs and AC
- Linear-search resource filtering and sorting
- Dictionary/hash-table lookup of resources by ID
- Booking creation with date/time overlap detection
- Booking cancellation and automatic promotion of the first eligible FIFO waiting-list request
- Remove a waiting-list request
- JSON persistence across application restarts
- Responsive desktop and mobile interface
- Input validation and user-friendly error messages

## Project structure

```text
campus_resource_optimizer/
├── app.py
├── database.json              # created automatically on first run
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

## Requirements

- Python 3.9 or newer
- Visual Studio Code
- Python extension for VS Code (recommended)
- A modern browser

## Run in VS Code (Windows)

1. Extract the project ZIP file.
2. Open VS Code.
3. Select **File → Open Folder** and choose `campus_resource_optimizer`.
4. Open the integrated terminal: **Terminal → New Terminal**.
5. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

6. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run this once in that terminal and activate again:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

7. Install Flask:

   ```powershell
   py -m pip install -r requirements.txt
   ```

8. Start the application:

   ```powershell
   py app.py
   ```

9. Open this address in your browser:

   `http://127.0.0.1:5000`

## Run on macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Then visit `http://127.0.0.1:5000`.

## First run and sample data

On the first launch, `database.json` is created automatically with five sample resources. You can add, edit or delete resources from the Resources page. Bookings and waiting-list entries are written to the same JSON file immediately after each successful operation.

To restore the original sample data, stop the server, delete `database.json`, and restart `python app.py`. **This permanently removes your current saved records.**

## DSA concepts used

| Concept | Where it is used |
|---|---|
| Linear Search | `/api/resources` scans resource records for matching text and type |
| Sorting | Resource list sorted by name or capacity; bookings sorted by date/time |
| Dictionary / Hash Table | `resource_index()` builds an ID-to-resource dictionary for average O(1) lookup |
| Queue (FIFO) | Waiting requests append at the end; promotion scans insertion order and confirms the first eligible request |

## Booking conflict logic

Two bookings conflict when they refer to the same resource and date and their time intervals overlap. Adjacent bookings are allowed (for example, 10:00–11:00 and 11:00–12:00). End time must be later than start time.

A conflicting request is retained in the waiting list. When a booking is cancelled, the app checks waiting requests for that resource in FIFO order and promotes the first request whose requested slot is now free.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/dashboard` | Dashboard statistics |
| GET | `/api/resources` | List/search/sort resources |
| POST | `/api/resources` | Add resource |
| PUT | `/api/resources/<id>` | Edit resource |
| DELETE | `/api/resources/<id>` | Delete resource |
| GET | `/api/bookings` | List bookings |
| POST | `/api/bookings` | Create booking or queue request |
| DELETE | `/api/bookings/<id>` | Cancel booking and promote eligible waiter |
| GET | `/api/waiting-list` | View FIFO queue |
| DELETE | `/api/waiting-list/<id>` | Remove a waiting request |

## Important notes

- This is a local academic/demo application, not a production multi-user service.
- Flask's development server is used. For deployment, use a production WSGI server and disable debug mode.
- JSON file writes are protected by an in-process lock and use a temporary file followed by an atomic replacement. For multiple server processes or concurrent deployments, use a transactional database.
- No authentication is included in this starter application. Do not expose it publicly with sensitive institutional data.
