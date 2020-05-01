import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    file = open("books.csv")
    reader = csv.reader(file)
    for isbn, title, author, published in reader:
        db.execute("INSERT INTO books (isbn, title, author, published) VALUES (:isbn, :title, :author, :published)",
                    {"isbn": isbn, "title": title, "author": author, "published": published})
    db.commit()
if __name__ == "__main__":
    main()