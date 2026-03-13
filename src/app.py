"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


# --- Persistencia con SQLAlchemy ---
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import IntegrityError

DATABASE_URL = "sqlite:///./activities.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    schedule = Column(String)
    max_participants = Column(Integer)
    participants = relationship("Participant", back_populates="activity", cascade="all, delete-orphan")

class Participant(Base):
    __tablename__ = "participants"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"))
    activity = relationship("Activity", back_populates="participants")
    __table_args__ = (UniqueConstraint('email', 'activity_id', name='_email_activity_uc'),)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Poblar con datos iniciales si la tabla está vacía
    db = SessionLocal()
    if db.query(Activity).count() == 0:
        initial_activities = [
            {"name": "Chess Club", "description": "Learn strategies and compete in chess tournaments", "schedule": "Fridays, 3:30 PM - 5:00 PM", "max_participants": 12, "participants": ["michael@mergington.edu", "daniel@mergington.edu"]},
            {"name": "Programming Class", "description": "Learn programming fundamentals and build software projects", "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM", "max_participants": 20, "participants": ["emma@mergington.edu", "sophia@mergington.edu"]},
            {"name": "Gym Class", "description": "Physical education and sports activities", "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM", "max_participants": 30, "participants": ["john@mergington.edu", "olivia@mergington.edu"]},
            {"name": "Soccer Team", "description": "Join the school soccer team and compete in matches", "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM", "max_participants": 22, "participants": ["liam@mergington.edu", "noah@mergington.edu"]},
            {"name": "Basketball Team", "description": "Practice and play basketball with the school team", "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM", "max_participants": 15, "participants": ["ava@mergington.edu", "mia@mergington.edu"]},
            {"name": "Art Club", "description": "Explore your creativity through painting and drawing", "schedule": "Thursdays, 3:30 PM - 5:00 PM", "max_participants": 15, "participants": ["amelia@mergington.edu", "harper@mergington.edu"]},
            {"name": "Drama Club", "description": "Act, direct, and produce plays and performances", "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM", "max_participants": 20, "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]},
            {"name": "Math Club", "description": "Solve challenging problems and participate in math competitions", "schedule": "Tuesdays, 3:30 PM - 4:30 PM", "max_participants": 10, "participants": ["james@mergington.edu", "benjamin@mergington.edu"]},
            {"name": "Debate Team", "description": "Develop public speaking and argumentation skills", "schedule": "Fridays, 4:00 PM - 5:30 PM", "max_participants": 12, "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]},
        ]
        for act in initial_activities:
            activity = Activity(
                name=act["name"],
                description=act["description"],
                schedule=act["schedule"],
                max_participants=act["max_participants"]
            )
            db.add(activity)
            db.flush()  # Para obtener el id
            for email in act["participants"]:
                db.add(Participant(email=email, activity=activity))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        finally:
            db.close()

@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")



@app.get("/activities")
def get_activities():
    db = SessionLocal()
    acts = db.query(Activity).all()
    result = {}
    for act in acts:
        result[act.name] = {
            "description": act.description,
            "schedule": act.schedule,
            "max_participants": act.max_participants,
            "participants": [p.email for p in act.participants]
        }
    db.close()
    return result



@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    db = SessionLocal()
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        db.close()
        raise HTTPException(status_code=404, detail="Activity not found")
    if db.query(Participant).filter(Participant.activity_id == activity.id, Participant.email == email).first():
        db.close()
        raise HTTPException(status_code=400, detail="Student is already signed up")
    if len(activity.participants) >= activity.max_participants:
        db.close()
        raise HTTPException(status_code=400, detail="Activity is full")
    try:
        db.add(Participant(email=email, activity=activity))
        db.commit()
    except IntegrityError:
        db.rollback()
        db.close()
        raise HTTPException(status_code=400, detail="Could not sign up student")
    db.close()
    return {"message": f"Signed up {email} for {activity_name}"}



@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    db = SessionLocal()
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        db.close()
        raise HTTPException(status_code=404, detail="Activity not found")
    participant = db.query(Participant).filter(Participant.activity_id == activity.id, Participant.email == email).first()
    if not participant:
        db.close()
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")
    db.delete(participant)
    db.commit()
    db.close()
    return {"message": f"Unregistered {email} from {activity_name}"}
