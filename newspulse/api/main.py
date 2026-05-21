from fastapi import FastAPI
from newspulse.db import init_db, seed_sources
from newspulse import scheduler
from newspulse.api import routes

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_db()
    seed_sources()
    scheduler.start()

app.include_router(routes.router)
