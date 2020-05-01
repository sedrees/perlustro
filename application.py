import os, requests

from flask import Flask, session, render_template, request, redirect, json, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Grab Goodreads Information and Return As [Rating, Rating Count]
def get_gr_info(isbn):
    gr_info = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "Mf3yklvvJiGbfHcnSRmxIg", "isbns": isbn})
    if gr_info.status_code !=200:
        raise Exception("API Request Unsuccessful")
    gr_data = gr_info.json()
    gr_rating = gr_data["books"][0]["average_rating"]
    gr_count = gr_data["books"][0]["work_ratings_count"]
    data =[gr_rating, gr_count]
    return data

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def reg():

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        if not request.form.get("username"):
            return render_template("error.html", message="must provide username")

        elif not request.form.get("password"):
            return render_template("error.html", message="must provide password")

        elif not request.form.get("confirm"):
            return render_template("error.html", message="must confirm password")
        
        # Existing user?
        username = request.form.get("username")
        user_exists = db.execute("SELECT * FROM users WHERE username = :username", {"username":username}).rowcount
        
        if user_exists:
            return render_template("error.html", message="username already exists")

        # Passwords match?
        if not request.form.get("password") == request.form.get("confirm"):
            return render_template("error.html", message="passwords must match")
        
        # Add new
        db.execute("INSERT INTO users (username, password, reg_time) VALUES (:username, :hash, :time)", 
                   {"username":username, 
                   "hash":generate_password_hash(request.form.get("password"), method='sha256', salt_length=8),
                   "time":"now()"})
        
        db.commit()

        # You can log in now
        return redirect("/")

    else: 
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        #Form data?
        if not username:
            return render_template("error.html", message="must provide username")

        elif not password:
            return render_template("error.html", message="must provide password")

        #User exists?
        user = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()

        #Verify
        if not user:
            return render_template("error.html", message="user doesn't exist")

        if not check_password_hash(user.password, password):
            return render_template("error.html", message="invalid password")

        #Login
        session["user_id"] = user.id
        return redirect("/search")

    else: 
        return render_template("login.html")

@app.route("/error")
def error():
    return render_template("error.html", message=message)

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form.get("query")

        if not query:
            return render_template("error.html", message="please provide query")

        result = db.execute("SELECT * from books WHERE isbn ILIKE :query OR author ILIKE :query OR title ILIKE :query", 
                            {"query": "%" + query + "%"}).fetchall()

        return render_template("result.html", result=result)
    else:
        return render_template("search.html")

@app.route("/details", methods=["GET", "POST"])
def details():
    isbn = request.args.get("isbn")
    book = db.execute("SELECT * from books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    if request.method == "POST":
        review = request.form.get("review")
        if review:
            db.execute("INSERT INTO reviews (isbn, content, user_id) VALUES (:isbn, :content, :user_id)",
                        {"isbn": isbn, "content": review, "user_id": session['user_id']})
            db.commit()
        return render_template("details.html", book = book, gr_rating = get_gr_info(isbn)[0], gr_count = get_gr_info(isbn)[1])
    else:
        return render_template("details.html", book = book, gr_rating = get_gr_info(isbn)[0], gr_count = get_gr_info(isbn)[1])

@app.route("/api/<string:isbn>")
def book_api(isbn):
    book = db.execute("SELECT * from books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    if not book:
        return jsonify({"error: Invalid ISBN"}), 422

    return jsonify({
        "title":book["title"],
        "author":book["author"],
        "year":book["published"],
        "isbn":book["isbn"],
        "review_count":get_gr_info(isbn)[1],
        "average_score":get_gr_info(isbn)[0]
    })