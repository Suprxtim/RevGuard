from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes import ui, api
from app.core.logger import logger

app = FastAPI(title=settings.PROJECT_NAME)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In strict production, lock this down
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Include the routers
app.include_router(ui.router)
app.include_router(api.router)

@app.get("/")
async def root():
    # Redirect to the audit dashboard as it is the primary view
    return RedirectResponse(url="/audit")
