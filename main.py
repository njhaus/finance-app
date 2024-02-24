from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import time
from datetime import datetime
import sys
import os

# Add current directory to the Python path
print('append filename')
sys.path.append(os.path.dirname(__file__))


print('app is found at least')
# from helpers import apology, login_required, lookup, usd
from helpers import apology, login_required, lookup, usd


# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

import os

# Get the current working directory
current_directory = os.getcwd()
print("Current working directory:", current_directory)


# Get a list of files and directories in the current working directory
files_in_directory = os.listdir(current_directory)
print("Files in the current directory:")
for file in files_in_directory:
    print(file)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


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
    # """Display stock quote."""
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        print(stock)
        if stock == None:
            return apology("We were unable to find information for the stock you provided.", 400)
        else:
            return render_template("quoted.html", symbol=stock["symbol"], price=usd(round(float(stock["price"]), 2)))
    # """Get stock quote."""
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        """Register user"""
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        existingUser = db.execute("SELECT * FROM users WHERE username = ?", username)
        hashedPassword = generate_password_hash(password, method='pbkdf2', salt_length=16)

        if not username or not password or not password == confirmation:
            return apology("Invalid username or password. Please try again", 400)
        elif existingUser:
            return apology("Username already exists. Please try again.", 400)
        else:
            #insert into database
            db.execute("INSERT INTO users ('username', 'hash') VALUES (?, ?)", username, hashedPassword)
            # Log in directly after registering
            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username = ?", username)

            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
                return apology("unable to login", 403)

            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]

            # Redirect user to home page
            return redirect("/")
    else :
        return render_template("register.html")



@app.route("/")
@login_required
def index():
    userId = session["user_id"]
    if not userId:
        return redirect("/login")
    # user data -- name and cash
    currUser = db.execute("SELECT * FROM users WHERE id = ?", userId)[0]
    print(currUser)
    # stock data -- symbol and number for each stock
    stockList = db.execute("SELECT symbol, number FROM stocks WHERE user_id = ?", currUser["id"])
    print(stockList)
    # stock data -- current price for each stock (make a dict)
    totalValue = float(currUser["cash"])
    for stock in stockList:
        stock["price"] = round(float(lookup(stock["symbol"])["price"]), 2)
        stock["number"] = round(float(stock["number"]))
        totalValue = round(float(totalValue) + (float(stock["price"]) * float(stock["number"])), 2)
        stock["total"] = usd((float(stock["price"]) * float(stock["number"])))
        stock["price"] = usd(stock["price"])
    # """Show portfolio of stocks"""
    # Get total of all stocks
    print(stockList)
    return render_template("index.html", username=currUser['username'], cash=usd(currUser["cash"]), stocks=stockList, totalValue=usd(round(totalValue, 2)))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    userId = session["user_id"]
    # """Buy and display index of stocks."""
    if request.method == "POST":
        # Get stock. Return apology if not found
        stock = lookup(request.form.get("symbol"))
        shareCheck = request.form.get("shares")
        if stock == None or not shareCheck.isnumeric() or float(shareCheck) < 1 or not (float(shareCheck)).is_integer():
            return apology("We were unable to find information for the stock you provided.", 400)
        shares = float(shareCheck)
        #Check if money is available
        userCash = db.execute("SELECT cash FROM users WHERE id = ?", userId)
        print(stock["price"])
        print(shares)
        print(userCash)
        totalPrice = float(stock["price"]) * float(shares)
        if float(userCash[0]["cash"]) < totalPrice:
            return apology("You do not have enough cash to complete this purchase.", 418)
        #Insert transaction
        db.execute("INSERT INTO transactions ('type','user_id', 'symbol', 'shares', price, 'timestamp') VALUES (?, ?, ?, ?, ?, ?)", 'buy', userId, stock["symbol"], shares, float(stock["price"]), int(time.time()))

        #If stock is already owned by user, update. If stock is not owned, insert new stock
        userOwned = db.execute("SELECT number FROM stocks WHERE user_id = ? AND symbol = ?", userId, stock["symbol"])
        if userOwned:
            db.execute("UPDATE stocks SET number = number + ? WHERE user_id = ? AND symbol = ?", shares, userId, stock["symbol"])
        else:
            db.execute("INSERT INTO stocks ('user_id', 'symbol', 'number') VALUES (?,?,?)", userId, stock["symbol"], shares)
        #     return render_template("quoted.html", symbol=stock["symbol"], price=stock["price"])
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", totalPrice, userId)
        return redirect("/")
    else:
        return render_template("buy.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    userId = session["user_id"]
    stockList = db.execute("SELECT symbol, number FROM stocks WHERE user_id = ?", userId)
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = float(request.form.get("shares"))
        targetStock = db.execute("SELECT symbol, number FROM stocks WHERE user_id = ? AND symbol = ?", userId, symbol)
        totalPrice = float(lookup(symbol)["price"]) * shares
        print(totalPrice)
        if not targetStock:
            return apology(f"You don't own any shares of {symbol}", 400)
        elif shares > float(targetStock[0]["number"]) or shares < 1 or not (shares).is_integer():
            return apology(f"You can't sell {shares} shares of {symbol}", 400)
        elif shares == float(targetStock[0]["number"]):
            db.execute("DELETE FROM stocks WHERE user_id = ? AND symbol = ?", userId, symbol)
        else:
            db.execute("UPDATE stocks SET number = number - ? WHERE user_id = ? AND symbol = ?", shares, userId, symbol)
        db.execute("INSERT INTO transactions ('type', 'user_id', 'symbol', 'shares', price, 'timestamp') VALUES (?, ?, ?, ?, ?, ?)", 'sell', userId, symbol, shares, float(lookup(symbol)["price"]), int(time.time()))
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", totalPrice, userId)
        return redirect("/")
    else:
        return render_template("sell.html", stocks=stockList)



@app.route("/history")
@login_required
def history():
    # """Show history of transactions"""
    userId = session["user_id"]
    currUser = db.execute("SELECT * FROM users WHERE id = ?", userId)[0]
    history = db.execute("SELECT * FROM transactions WHERE user_id = ?", userId)
    for transaction in history:
        transaction["price"] = usd(float(transaction["shares"]) * float(transaction["price"]))
        transaction["timestamp"] = datetime.fromtimestamp(int(transaction["timestamp"]))
    return render_template("history.html", history=history, username=currUser["username"])



if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
