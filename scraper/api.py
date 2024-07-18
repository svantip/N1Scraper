from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, String, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import date, time

# Definiranje baze podataka
DATABASE_URL = "sqlite:///N1Scraper/data/articles.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Article(Base):
    __tablename__ = "articles"
    article_id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    date = Column(Date)
    time = Column(Time)
    hashtags = Column(String)
    text = Column(String)
    source = Column(String)
    category = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()

class ArticleResponse(BaseModel):
    article_id: str
    title: str
    date: str
    time: str
    hashtags: str
    text: str
    source: str
    category: str

    class Config:
        orm_mode = True

@app.get("/articles", response_model=List[ArticleResponse])
def read_articles(skip: int = 0, limit: int = 10):
    db = SessionLocal()
    articles = db.query(Article).offset(skip).limit(limit).all()
    response_articles = []
    for article in articles:
        response_articles.append(ArticleResponse(
            article_id=article.article_id,
            title=article.title,
            date=article.date.isoformat() if article.date else None,
            time=article.time.isoformat() if article.time else None,
            hashtags=article.hashtags,
            text=article.text,
            source=article.source,
            category=article.category
        ))
    db.close()
    return response_articles

@app.get("/articles/{article_id}", response_model=ArticleResponse)
def read_article(article_id: str):
    db = SessionLocal()
    article = db.query(Article).filter(Article.article_id == article_id).first()
    db.close()
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleResponse(
        article_id=article.article_id,
        title=article.title,
        date=article.date.isoformat() if article.date else None,
        time=article.time.isoformat() if article.time else None,
        hashtags=article.hashtags,
        text=article.text,
        source=article.source,
        category=article.category
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
