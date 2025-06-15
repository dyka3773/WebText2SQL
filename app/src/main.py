import os
from collections.abc import Generator
from typing import Annotated, Any

import custom_logging
from auth import hash_password, verify_password
from chainlit.utils import mount_chainlit
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer
from sqlmodel import Session, create_engine
from starlette.templating import _TemplateResponse
from user_controllers import app_users

load_dotenv()

templates = Jinja2Templates(directory="templates")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)

logger = custom_logging.setup_logger("fastapi")

SECRET_KEY = os.getenv("SECRET_KEY")
COOKIE_NAME = os.getenv("COOKIE_NAME")
serializer = URLSafeTimedSerializer(SECRET_KEY)
db_engine = create_engine(os.getenv("DATABASE_URL"))


def get_session() -> Generator[Session, Any]:
    with Session(db_engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/public", StaticFiles(directory="public"), name="public")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None) -> _TemplateResponse:
    """Render the login page with an optional error message."""
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/login", response_model=None)
def login(
    response: Response,
    request: Request,
    session: SessionDep,
    email: Annotated[str, Form()] = ...,
    password: Annotated[str, Form()] = ...,
) -> _TemplateResponse | RedirectResponse:
    """Handle user login, verify credentials, and set a session cookie."""
    if not email or not password:
        error_message = "Email and password are required"
        return templates.TemplateResponse("login.html", {"request": request, "error": error_message}, status_code=400)

    user = app_users.get_app_user_by_email(email=email, session=session)

    if not user or not verify_password(password, user.hashed_password):
        error_message = "Password is incorrect"

        if not user:
            error_message = "User does not exist"

        logger.warning(f"Login failed for user: {email}")

        return templates.TemplateResponse("login.html", {"request": request, "error": error_message}, status_code=401)

    token = serializer.dumps(email)

    response = RedirectResponse(url="/chainlit", status_code=302)
    response.set_cookie(COOKIE_NAME, token, httponly=True)

    logger.info(f"User logged in successfully: {email}")

    return response


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, error: str | None = None) -> _TemplateResponse:
    """Render the registration page with an optional error message."""
    return templates.TemplateResponse("register.html", {"request": request, "error": error})


@app.post("/register", response_model=None)
def register(
    response: Response,
    request: Request,
    session: SessionDep,
    email: Annotated[str, Form()] = ...,
    password: Annotated[str, Form()] = ...,
) -> _TemplateResponse | RedirectResponse:
    """Handle user registration, create a new user, and set a session cookie."""
    if not email or not password:
        error_message = "Email and password are required"
        return templates.TemplateResponse("register.html", {"request": request, "error": error_message}, status_code=400)

    if app_users.app_user_exists(email=email, session=session):
        error_message = "User already exists"
        logger.warning(f"Registration failed: User already exists with email {email}")
        return templates.TemplateResponse("register.html", {"request": request, "error": error_message}, status_code=400)

    # Create a new user
    app_users.insert_app_user(
        app_users.AppUser(
            email=email,
            username=email.split("@")[0],
            hashed_password=hash_password(password),
        ),
        session=session,
    )

    token = serializer.dumps(email)
    response = RedirectResponse(url="/chainlit", status_code=302)
    response.set_cookie(COOKIE_NAME, token, httponly=True)

    logger.info(f"User registered successfully: {email}")

    return response


@app.get("/", response_class=HTMLResponse)
def home(_: Request) -> RedirectResponse:
    """Redirect to the login page."""
    return RedirectResponse(url="/login", status_code=302)


@app.get("/favicon")
def favicon(_: Request) -> RedirectResponse:
    """Redirect to the favicon."""
    return RedirectResponse(url="/public/favicon.png", status_code=302)


mount_chainlit(app=app, target="chainlit_app.py", path="/chainlit")
