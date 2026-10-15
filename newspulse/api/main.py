import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from newspulse import scheduler
from newspulse.api import routes
from newspulse.db import ROOT, init_db, seed_sources

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_sources()
    # WORLDBRIEF_NO_SCHEDULER=1 serves the dashboard without fetching or calling the LLM.
    jobs = None if os.getenv("WORLDBRIEF_NO_SCHEDULER") else scheduler.start()
    yield
    if jobs:
        jobs.shutdown(wait=False)


app = FastAPI(title="WorldBrief", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "templates" / "index.html")


app.include_router(routes.router)
