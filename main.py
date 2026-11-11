from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, Session, create_engine, select

app = FastAPI(title="投稿與審查系統 API")

# 跨域設定 (若前後端分離)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 建立 PostgreSQL 連線
DATABASE_URL = "postgresql+psycopg2://postgres:qwert123@localhost:5432/mydb"
engine = create_engine(DATABASE_URL)

class Submission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    category: str
    content: str
    status: str = "編輯中"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

def get_session():
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

# 1. 取得所有稿件
@app.get("/api/submissions")
def get_submissions(session: Session = Depends(get_session)):
    submissions = session.exec(select(Submission)).all()
    return submissions

# 2. 新增投稿
@app.post("/api/submissions")
def create_submission(sub: Submission, session: Session = Depends(get_session)):
    sub.updated_at = datetime.now(timezone.utc)
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub

# 3. 編輯投稿 (僅限編輯中)
@app.put("/api/submissions/{sub_id}")
def update_submission(sub_id: int, updated_data: Submission, session: Session = Depends(get_session)):
    sub = session.get(Submission, sub_id)
    if not sub:
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

# 4. 刪除稿件 (僅限編輯中)
@app.delete("/api/submissions/{sub_id}")
def delete_submission(sub_id: int, session: Session = Depends(get_session)):
    sub = session.get(Submission, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="找不到此稿件")
    if sub.status != "編輯中":
        raise HTTPException(status_code=400, detail="只能刪除編輯中的稿件")
    
    session.delete(sub)
    session.commit()
    return {"ok": True}

# 5. 狀態轉換：送出投稿 (編輯中 -> 審查中)
@app.post("/api/submissions/{sub_id}/submit")
def submit_review(sub_id: int, session: Session = Depends(get_session)):
    sub = session.get(Submission, sub_id)
    if not sub or sub.status != "編輯中":
        raise HTTPException(status_code=400, detail="狀態不符，無法送出")
    sub.status = "審查中"
    sub.updated_at = datetime.now(timezone.utc)
    session.add(sub)
    session.commit()
    return sub

# 6. 編輯審查：通過 (審查中 -> 已通過) 或 退回 (審查中 -> 編輯中)
@app.post("/api/submissions/{sub_id}/review")
def review_submission(sub_id: int, action: str, session: Session = Depends(get_session)):
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