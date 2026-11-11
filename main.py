from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field as PydanticField
from sqlalchemy import inspect, text
from sqlmodel import Field, Session, SQLModel, create_engine, select

app = FastAPI(title="投稿與審查系統 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    env_file = Path(__file__).with_name(".env")
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == "DATABASE_URL":
                database_url = value.strip().strip("\"'")
                if database_url:
                    return database_url

    raise RuntimeError(
        "DATABASE_URL is not configured. Set it in the environment or project .env file."
    )


DATABASE_URL = get_database_url()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
PASSWORD_ITERATIONS = 600_000
SESSION_LIFETIME = timedelta(days=7)
bearer_scheme = HTTPBearer(auto_error=False)


class Account(SQLModel, table=True):
    __tablename__ = "account"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    display_name: str = Field(max_length=80)
    role: str = Field(max_length=10)
    password_hash: str


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="account.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    expires_at: datetime


class Submission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    category: str
    content: str
    status: str = "編輯中"
    author_name: str = Field(default="一般作者", max_length=80)
    owner_id: Optional[int] = Field(default=None, foreign_key="account.id")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RegisterRequest(BaseModel):
    username: str = PydanticField(min_length=1, max_length=50)
    display_name: str = PydanticField(min_length=1, max_length=80)
    password: str = PydanticField(min_length=8)
    role: Literal["author", "editor"]


class LoginRequest(BaseModel):
    username: str = PydanticField(min_length=1, max_length=50)
    password: str = PydanticField(min_length=8)
    role: Literal["author", "editor"]


class SubmissionInput(BaseModel):
    title: str
    category: str
    content: str


def get_session():
    with Session(engine) as session:
        yield session


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"{salt.hex()}:{password_digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_hex, digest_hex = password_hash.split(":", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except ValueError:
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def account_response(account: Account) -> dict:
    return {
        "id": account.id,
        "username": account.username,
        "display_name": account.display_name,
        "role": account.role,
    }


def create_auth_session(account: Account, session: Session) -> dict:
    token = secrets.token_urlsafe(32)
    auth_session = AuthSession(
        user_id=account.id,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(timezone.utc) + SESSION_LIFETIME,
    )
    session.add(auth_session)
    session.commit()
    return {"token": token, "user": account_response(account)}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> Account:
    if credentials is None:
        raise HTTPException(status_code=401, detail="請先登入")

    token_hash = hashlib.sha256(credentials.credentials.encode("utf-8")).hexdigest()
    auth_session = session.exec(
        select(AuthSession).where(
            AuthSession.token_hash == token_hash,
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
    ).first()
    if auth_session is None:
        raise HTTPException(status_code=401, detail="登入已逾期，請重新登入")

    account = session.get(Account, auth_session.user_id)
    if account is None:
        raise HTTPException(status_code=401, detail="找不到登入帳號")
    return account


def require_role(account: Account, role: str) -> None:
    if account.role != role:
        raise HTTPException(status_code=403, detail="此操作不符合您的帳號身份")


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        columns = {
            column["name"] for column in inspect(connection).get_columns("submission")
        }
        if "author_name" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE submission ADD COLUMN "
                    "author_name VARCHAR(80) NOT NULL DEFAULT '一般作者'"
                )
            )
        if "owner_id" not in columns:
            connection.execute(
                text("ALTER TABLE submission ADD COLUMN owner_id INTEGER")
            )


@app.post("/api/auth/register")
def register_account(
    request: RegisterRequest, session: Session = Depends(get_session)
):
    account = Account(
        username=request.username.strip(),
        display_name=request.display_name.strip(),
        role=request.role,
        password_hash=hash_password(request.password),
    )
    if not account.username or not account.display_name:
        raise HTTPException(status_code=422, detail="使用者名稱和顯示名稱不可空白")
    if session.exec(
        select(Account).where(Account.username == account.username)
    ).first():
        raise HTTPException(status_code=409, detail="使用者名稱已被使用")

    session.add(account)
    session.commit()
    session.refresh(account)
    return create_auth_session(account, session)


@app.post("/api/auth/login")
def login(
    request: LoginRequest, session: Session = Depends(get_session)
):
    account = session.exec(
        select(Account).where(Account.username == request.username.strip())
    ).first()
    if (
        account is None
        or account.role != request.role
        or not verify_password(request.password, account.password_hash)
    ):
        raise HTTPException(status_code=401, detail="使用者名稱、身份或密碼錯誤")
    return create_auth_session(account, session)


@app.get("/api/auth/me")
def get_account(account: Account = Depends(get_current_user)):
    return account_response(account)


@app.post("/api/auth/logout", dependencies=[Depends(get_current_user)])
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
):
    if credentials is not None:
        token_hash = hashlib.sha256(credentials.credentials.encode("utf-8")).hexdigest()
        auth_session = session.exec(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        ).first()
        if auth_session is not None:
            session.delete(auth_session)
            session.commit()
    return {"ok": True}


@app.get("/api/submissions")
def get_submissions(
    session: Session = Depends(get_session),
    account: Account = Depends(get_current_user),
):
    statement = select(Submission)
    if account.role == "author":
        statement = statement.where(Submission.owner_id == account.id)
    return session.exec(statement).all()


@app.post("/api/submissions")
def create_submission(
    sub: SubmissionInput,
    session: Session = Depends(get_session),
    account: Account = Depends(get_current_user),
):
    require_role(account, "author")
    submission = Submission(
        title=sub.title,
        category=sub.category,
        content=sub.content,
        author_name=account.display_name,
        owner_id=account.id,
        updated_at=datetime.now(timezone.utc),
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return submission


@app.put("/api/submissions/{sub_id}")
def update_submission(
    sub_id: int,
    updated_data: SubmissionInput,
    session: Session = Depends(get_session),
    account: Account = Depends(get_current_user),
):
    require_role(account, "author")
    sub = session.get(Submission, sub_id)
    if not sub or sub.owner_id != account.id:
        raise HTTPException(status_code=404, detail="找不到此稿件")
    if sub.status != "編輯中":
        raise HTTPException(status_code=400, detail="只能修改編輯中的稿件")

    sub.title = updated_data.title
    sub.category = updated_data.category
    sub.content = updated_data.content
    sub.updated_at = datetime.now(timezone.utc)

    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub


@app.delete("/api/submissions/{sub_id}")
def delete_submission(
    sub_id: int,
    session: Session = Depends(get_session),
    account: Account = Depends(get_current_user),
):
    require_role(account, "author")
    sub = session.get(Submission, sub_id)
    if not sub or sub.owner_id != account.id:
        raise HTTPException(status_code=404, detail="找不到此稿件")
    if sub.status != "編輯中":
        raise HTTPException(status_code=400, detail="只能刪除編輯中的稿件")

    session.delete(sub)
    session.commit()
    return {"ok": True}


@app.post("/api/submissions/{sub_id}/submit")
def submit_review(
    sub_id: int,
    session: Session = Depends(get_session),
    account: Account = Depends(get_current_user),
):
    require_role(account, "author")
    sub = session.get(Submission, sub_id)
    if not sub or sub.owner_id != account.id or sub.status != "編輯中":
        raise HTTPException(status_code=400, detail="狀態不符，無法送出")
    sub.status = "審查中"
    sub.updated_at = datetime.now(timezone.utc)
    session.add(sub)
    session.commit()
    return sub


@app.post("/api/submissions/{sub_id}/review")
def review_submission(
    sub_id: int,
    action: str,
    session: Session = Depends(get_session),
    account: Account = Depends(get_current_user),
):
    require_role(account, "editor")
    sub = session.get(Submission, sub_id)
    if not sub or sub.status != "審查中":
        raise HTTPException(status_code=400, detail="狀態不符，無法審查")

    if action == "approve":
        sub.status = "已通過"
    elif action == "reject":
        sub.status = "編輯中"
    else:
        raise HTTPException(status_code=400, detail="無效的操作")

    sub.updated_at = datetime.now(timezone.utc)
    session.add(sub)
    session.commit()
    return sub
