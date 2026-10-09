# Campus Resource Optimizer

## Description

A simple web application for a college to manage classrooms, computer labs, seminar halls and auditoriums.

It helps you to:

- add, view, edit and delete campus resources
- search resources by type, capacity, building and availability
- book a resource and prevent double booking
- get a recommendation for the most suitable room for a group of students

Workflow: **Add Resources → View/Search Resources → Check Availability → Book Resource → Detect Conflicts → Recommend Suitable Resource**

## Technologies

```text
Python
Flask
MySQL
HTML
CSS
JavaScript
```

## Installation

Open the project folder in VS Code, open the terminal (Terminal → New Terminal) and run:

```bash
python -m venv venv
```

Activate the virtual environment on Windows:

```bash
venv\Scripts\activate
```

(On Mac/Linux use `source venv/bin/activate`.)

Install the requirements:

```bash
pip install -r requirements.txt
```

## MySQL Setup

1. Open **MySQL Workbench** and connect to your local MySQL server.
2. Open the file `database/schema.sql` (File → Open SQL Script).
3. Run the whole script with the lightning bolt button. It creates the `campus_optimizer` database, both tables, sample resources and sample bookings.
   (Running it again deletes all data and restores the sample data.)
4. Create your `.env` file by copying `.env.example`:

   ```bash
   copy .env.example .env
   ```

   (On Mac/Linux: `cp .env.example .env`.) Then open `.env` and write your real MySQL password:

   ```text
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=campus_optimizer
   ```

Never share your `.env` file. It is listed in `.gitignore`, so GitHub will not receive it.

## Run Project

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Try the conflict detection

The sample data has a booking for **A-101 today from 10:00 AM to 11:00 AM**.

1. Go to **Bookings**.
2. Choose A-101, today's date, 10:30 to 11:30, 40 students, any purpose.
3. Click **Book resource**. You will see the booking conflict message and the request is placed on the waiting list.
4. Cancel the 10:00 booking. The waiting request is booked automatically.

Try 11:00 to 12:00 instead: it is accepted, because it starts exactly when the other booking ends.

## Folder Structure

```text
campus-resource-optimizer/
├── app.py                   Main Flask file: web pages (routes), booking logic, search, sort, queue, recommendation
├── database.py              Connects to MySQL and holds every SQL query
├── requirements.txt         Python packages to install
├── README.md                This file
├── .env.example             Template for your database settings (copy it to .env)
├── .gitignore               Tells Git to ignore .env, venv and cache files
│
├── database/
│   └── schema.sql           Creates the database, tables, sample resources and sample bookings
│
├── templates/               HTML pages (Flask fills in the data)
│   ├── index.html           Home / dashboard
│   ├── resources.html       Resource list, search, add, edit, delete
│   ├── bookings.html        Booking form, existing bookings, waiting list
│   └── recommendation.html  Recommendation form and results
│
├── static/
│   ├── style.css            Colours and layout (blue, white, light grey)
│   └── script.js            Small helpers: confirm messages, time check, "Check availability" button
│
└── ml/
    └── prediction.py        Optional placeholder for future demand prediction (not used by the website)
```

## Where the DSA is used

| Concept | Where | What it does |
| --- | --- | --- |
| Searching | `search_resources()` in `app.py` | Goes through all resources and keeps the ones that match the filters |
| Sorting | `sort_resources()` in `app.py` | Sorts by name, capacity or availability using `sorted()` |
| Dictionary (hash table) | `build_resource_dict()` in `app.py` | Finds a resource by its ID instantly |
| Queue | `waiting_queue` in `app.py` | First come, first served waiting list for bookings that had a conflict |

## GitHub

Install Git first, create an empty repository on GitHub, then run:

```bash
git init
git add .
git commit -m "Initial project"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

## Common problems

- **"Database error" page**: MySQL is not running, the password in `.env` is wrong, or `schema.sql` has not been run yet.
- **`ModuleNotFoundError`**: the virtual environment is not active. Run `venv\Scripts\activate` and `pip install -r requirements.txt` again.
- **Port already in use**: close the other program using port 5000, or change `app.run(debug=True)` to `app.run(debug=True, port=5001)` in `app.py`.
