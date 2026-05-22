from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from newspulse.db import init_db, seed_sources
from newspulse import scheduler
from newspulse.api import routes

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    init_db()
    seed_sources()
    scheduler.start()

@app.get("/")
def index():
    return FileResponse("templates/index.html")

app.include_router(routes.router)
