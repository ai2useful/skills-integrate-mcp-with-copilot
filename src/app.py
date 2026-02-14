"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import Request
import os
from pathlib import Path
import json
import uuid

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Load activities from JSON file (move data out of Python source)
DATA_DIR = current_dir.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
ACTIVITIES_FILE = DATA_DIR / "activities.json"
TEACHERS_FILE = DATA_DIR / "teachers.json"


def load_activities():
    if ACTIVITIES_FILE.exists():
        with open(ACTIVITIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_activities(activities):
    with open(ACTIVITIES_FILE, "w", encoding="utf-8") as f:
        json.dump(activities, f, indent=2)


def load_teachers():
    if TEACHERS_FILE.exists():
        with open(TEACHERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("teachers", [])
    return []


# In-memory state for simplicity
activities = load_activities()
_teacher_sessions = {}  # token -> username


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/admin/login")
def admin_login(payload: dict):
    """Simple login endpoint for teachers. Returns a token to use in `X-Admin-Token`."""
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    teachers = load_teachers()
    for t in teachers:
        if t.get("username") == username and t.get("password") == password:
            token = str(uuid.uuid4())
            _teacher_sessions[token] = username
            return {"token": token}

    raise HTTPException(status_code=401, detail="invalid credentials")


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, x_admin_token: str = Header(None)):
    """Register a student for an activity. Restricted to logged-in teachers (admin token required)."""
    # Require admin token
    if not x_admin_token or x_admin_token not in _teacher_sessions:
        raise HTTPException(status_code=401, detail="admin token required")

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity.get("participants", []):
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity.setdefault("participants", []).append(email)
    save_activities(activities)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, x_admin_token: str = Header(None)):
    """Unregister a student from an activity. Restricted to logged-in teachers."""
    if not x_admin_token or x_admin_token not in _teacher_sessions:
        raise HTTPException(status_code=401, detail="admin token required")

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity.get("participants", []):
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    save_activities(activities)
    return {"message": f"Unregistered {email} from {activity_name}"}
