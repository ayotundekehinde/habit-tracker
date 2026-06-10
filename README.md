# Habit Tracker

A full-stack habit tracking web app for building consistent daily routines. Create habits, check them off each day, track streaks, and monitor your completion rate — all synced to your account across devices.

## Features

- **User accounts** — Register and log in to keep habits tied to your profile
- **Daily check-ins** — Mark habits complete with a single click; toggle off if you checked by mistake
- **Streak tracking** — See how many consecutive days you've kept each habit going
- **Categories** — Organize habits by Study, Fitness, Monetization, Personal Development, or Other
- **Category filters** — Focus on one area at a time
- **Progress dashboard** — View total habits, today's completions, and your daily completion rate
- **Dark mode** — Switch themes; your preference is saved to your account
- **Legacy import** — Habits stored in browser local storage from an earlier version are automatically imported when you sign up or log in

## Tech Stack

| Layer    | Technology                          |
| -------- | ----------------------------------- |
| Frontend | HTML, CSS, vanilla JavaScript       |
| Backend  | Python, Flask                       |
| Database | SQLite                              |
| Auth     | JWT (PyJWT), bcrypt password hashes |

## Getting Started

### Prerequisites

- Python 3.10 or newer
- pip

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/ayotundekehinde/habit-tracker.git
   cd habit-tracker
   ```

2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

### Running the App

Start the Flask server:

```bash
python server.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. The server serves both the API and the frontend from a single process.

On first run, a SQLite database (`habit_tracker.db`) is created automatically in the project root.

## Usage

1. **Sign up** with a username (3+ characters) and password (6+ characters), or log in to an existing account.
2. **Add habits** using the form at the top — pick a name and category, then click **Add Habit**.
3. **Check off habits** each day using the checkbox next to each item.
4. **Filter** the list by category using the dropdown above your habit list.
5. **Toggle dark mode** with the moon/sun button in the header.

Your session stays active for 7 days via a stored JWT token.

## Project Structure

```
habit-tracker/
├── index.html       # App layout and auth UI
├── style.css        # Styling, light/dark themes
├── script.js        # Frontend logic and API client
├── server.py        # Flask API and static file server
├── habits.py        # Core habit/streak logic (Python module)
├── requirements.txt # Python dependencies
└── assets/          # Static assets
```

## API Overview

All authenticated endpoints require a `Bearer` token in the `Authorization` header.

| Method | Endpoint                      | Description                    |
| ------ | ----------------------------- | ------------------------------ |
| POST   | `/api/register`               | Create a new account           |
| POST   | `/api/login`                  | Log in and receive a JWT       |
| GET    | `/api/me`                     | Get current user info          |
| GET    | `/api/habits`                 | List all habits for the user   |
| POST   | `/api/habits`                 | Create a habit                 |
| POST   | `/api/habits/:id/toggle`      | Toggle today's completion      |
| DELETE | `/api/habits/:id`             | Delete a habit                 |
| POST   | `/api/habits/import`          | Import habits from local data  |
| PUT    | `/api/preferences`            | Update theme (`light` / `dark`)|

## Configuration

| Variable     | Default                                      | Description                          |
| ------------ | -------------------------------------------- | ------------------------------------ |
| `SECRET_KEY` | `dev-secret-change-in-production-...`        | JWT signing key — **set this in production** |

Example:

```bash
# Windows (PowerShell)
$env:SECRET_KEY = "your-secure-random-key-at-least-32-chars"

# macOS / Linux
export SECRET_KEY="your-secure-random-key-at-least-32-chars"
```

## Development Notes

- The database file (`habit_tracker.db`) and Python cache directories are gitignored.
- `habits.py` contains a standalone `Habit` / `HabitTracker` module used for core streak logic; the live app persists data through the Flask API and SQLite.
- Flask runs in debug mode when started via `python server.py` — disable this before deploying to production.

## License

This project is open source. Feel free to use and modify it for personal or educational purposes.
