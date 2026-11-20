from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api
from app.core.config import settings
from app.core.security import RateLimiter
from app.websocket.rooms import RoomHub, router as websocket


def create_app() -> FastAPI:
    app = FastAPI(title="FoodMatch", version="0.1.0")
    app.state.hub = RoomHub()
    app.state.limits = RateLimiter()

    @app.middleware("http")
    async def private_responses(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError):
        errors = error.errors()
        detail = next((item["msg"].removeprefix("Value error, ") for item in errors if item["type"] == "value_error"), None)
        return JSONResponse(status_code=422, content={"detail": detail or "Check the fields and try again."})

    app.add_middleware(
        CORSMiddleware, allow_origins=settings().cors_origins,
        allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-Restaurant-Ids"],
    )
    app.include_router(api)
    app.include_router(websocket)
    return app


app = create_app()
