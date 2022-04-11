import os
import psycopg2
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd
from datetime import datetime
now = datetime.now()
now.strftime('%m/%d/%Y')
'09/15/2013'

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL(os.environ.get("DATABASE_URL")
or "sqlite:///finance.db")

# Make sure API key is set

if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    stocks = db.execute("SELECT symbol, total, SUM(shares) as shares,price, time FROM transactions WHERE user_id = ? GROUP BY symbol", session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]

    totals = 0

    totals = cash

    for stock in stocks:
        totals += stock['total']

    return render_template("homepage.html", stocks=stocks, cash=cash, usd=usd, totals=totals)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        shares = int(request.form.get("shares"))
        print(shares)
        symbol = request.form.get("symbol")
        #print(lookup(symbol['name']))

        if not symbol:
            return apology("Enter a valid stock symbol", 403)

        if not shares:
            return apology("Enter a shares value", 403)

        if shares <= 0:
            return apology("Must enter a positive number")

        price = [lookup(symbol)['price']]
        print(price)

        price2 = float(price[0]) * shares
        print(price2)

        cash = db.execute("SELECT cash FROM users WHERE id = ?;", session["user_id"])[0]["cash"]
        newcash= cash - price2
        db.execute("UPDATE users SET cash = ? WHERE id = ?", newcash, session["user_id"])
        print(cash)

        if cash < price2:
            return apology("broke ass nigga, not enough cash")


        db.execute("INSERT INTO transactions (symbol, shares, total, price, time, user_id) VALUES(?,?,?,?,?,?);", symbol, shares, price2, price, now, session["user_id"])

        price2 = 0

        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    stocks = db.execute("SELECT shares, symbol, time, price FROM transactions WHERE user_id = ?", session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]

    totals = cash

    return render_template("history.html", stocks=stocks, usd=usd)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol= request.form.get("symbol")
        if symbol == None:
            return apology("write a symbol", 404)
        lookup(symbol)
        print(lookup(symbol))
        return render_template("quoted.html", symbol=lookup(symbol))
    else:
        return render_template("quote.html")





@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        name = request.form.get("username")
        Password = request.form.get("matchpassword")
        Password2 = request.form.get("Password")
        if Password != Password2:
            return apology("password not match", 404)

        password = generate_password_hash(Password, method='pbkdf2:sha256', salt_length=8)

        insert = "INSERT INTO users (username, hash) VALUES(?,?);"
        db.execute(insert, name, password)
        return redirect("/login")

    else:
        return render_template("register.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        if shares <= 0:
            return apology("not enough shares")

        sharess = db.execute("SELECT shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol", session["user_id"], symbol)[0]["shares"]
        price = lookup(symbol)['price']
        name = lookup(symbol)['name']
        sharesPrice = shares * price
        if shares > sharess:
            return apology(">:(")

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        db.execute("UPDATE transactions SET total = ? WHERE id = ?", sharesPrice, session["user_id"])
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash + sharesPrice, session["user_id"])
        db.execute("INSERT INTO transactions (symbol, shares, total, price, time, user_id) VALUES(?,?,?,?,?,?)", symbol, -shares, sharesPrice, price, now, session["user_id"])





        return redirect("/")

    else:
        symbols = db.execute("SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol" , session["user_id"])
        return render_template("sell.html", symbols=symbols)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
