from fastapi import FastAPI
from api.routers import auth, summarize
from db.database import engine
from db.models import user, history

# Create database tables
user.Base.metadata.create_all(bind=engine)
history.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include routers
app.include_router(auth.router)
app.include_router(summarize.router)