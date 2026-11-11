from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

class Submission(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    category: str
    content: str
    status: str = "編輯中"  # 狀態：編輯中, 審查中, 已通過
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))