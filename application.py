from flask import Flask, jsonify, render_template, request, url_for, session, redirect
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from cs50 import SQL
from datetime import datetime, date, timedelta

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///myproject.db")

@app.route("/add", methods=["POST"])
@login_required
def add():

    product = request.form.get("product_name")
    quantity = request.form.get("quantity")
    unit = request.form.get("units")
    shelf_life = int(request.form.get("shelf-life"))
    manufactured_date_str = request.form.get("date-of-manufacture")
    user_id = session["user_id"]

    if not manufactured_date_str:
        manufactured_date = date.today()
    else:
        manufactured_date = datetime.strptime(manufactured_date_str, "%Y-%m-%d").date()

    manufactured_date_db = manufactured_date.isoformat()
    expiration_date = manufactured_date + timedelta(days=shelf_life)
    expiration_date_db = expiration_date.isoformat()

    db.execute("INSERT INTO products (name, quantity, units, manufactured_date, expiration_date, user_id) VALUES (:name, :quantity, :units, :manufactured_date, :expiration_date, :user_id)",
    name=product, quantity=quantity, units=unit, manufactured_date=manufactured_date_db, expiration_date=expiration_date_db, user_id=user_id)

    return redirect(url_for("index"))

@app.route("/reduce", methods=["POST"])
@login_required
def reduce():
    productID = request.form.get("product")
    reduced_quantity = float(request.form.get("quantity"))
    user_id = session["user_id"]

    # TODO if reducing product's quantity is more than existing product's quantity
    products = db.execute("SELECT quantity FROM products WHERE user_id=:user_id AND id=:id", user_id=user_id, id=productID)
    product_quantity = float(products[0]["quantity"])
    new_quantity = product_quantity - reduced_quantity
    if new_quantity > 0:
        db.execute("UPDATE products SET quantity=:new_quantity WHERE user_id=:user_id AND id=:id", new_quantity=new_quantity, user_id=user_id, id=productID)
    else:
        db.execute("DELETE FROM products WHERE user_id=:user_id AND id=:id", user_id=user_id, id=productID)
    return redirect(url_for("index"))

@app.route("/remove", methods=["POST"])
@login_required
def remove():
    productID = request.form.get("product")
    user_id = session["user_id"]
    db.execute("DELETE FROM products WHERE user_id=:user_id AND id=:id", user_id=user_id, id=productID)
    return redirect(url_for("index"))

@app.route("/")
@login_required
def index():

    user_id = session["user_id"]
    products = db.execute("SELECT id, name, quantity, units, expiration_date FROM products WHERE user_id=:user_id ORDER BY expiration_date", user_id=user_id)

    return render_template("index.html", products=products)



@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return render_template("login.html", error="Wrong username or password!")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # security
        hashed_password = pwd_context.hash(request.form.get("password"))

        # add user to database
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
        username = request.form.get("username"), hash = hashed_password)

        # logging in
        if not result:
            return render_template("register.html", error="Have you already registered?")

        else:
            # query database for username
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

            # remember which user has logged in
            session["user_id"] = rows[0]["id"]

            # redirect user to home page
            return redirect(url_for("index"))

    else:
        return render_template("register.html")

