from fastapi import FastAPI, Depends
from api.routers import auth, summarize
from db.database import engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from db.models import user, history
from api.dependencies import get_db

# Create database tables
user.Base.metadata.create_all(bind=engine)
history.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include routers
app.include_router(auth.router)
app.include_router(summarize.router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))  # Correct way
        return {"status": "Server is running", "db": "Connected"}
    except Exception as e:
        return {"status": "Server is running", "db": f"Connection failed: {str(e)}"}