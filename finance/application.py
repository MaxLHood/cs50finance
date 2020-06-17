import os
import pandas
import requests

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
#pk_e2fa49fd66144720aa53c0237c97d915 
from helpers import apology, login_required, lookup, usd

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
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return render_template("index.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    if "buytester" not in session:        
        session["buytester"] = {}

    if request.method == "POST":
        session['buytester']["qty"]=request.form.get("QTY")
        session['buytester']["value"]=lookup(request.form.get("TICKER"))["price"]
        session['buytester']["name"]=lookup(request.form.get("TICKER"))["name"]
        
        #print(type(session['buytester']["value"]))
        #print(type(session['buytester']["name"]))
        #print(type(session['buytester']["qty"]))

        row = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        if row[0]['cash']>int(session['buytester']["qty"])*session['buytester']["value"]:
            cashafter=row[0]['cash']-int(session['buytester']["qty"])*session['buytester']["value"]
            db.execute("UPDATE users SET cash=:ca WHERE id=:uid", ca=cashafter, uid=session['user_id'])

            cheq=db.execute("SELECT * FROM  holdings WHERE userid=:uid AND ticker=:tick", uid=session['user_id'], tick=request.form.get("TICKER"))
            if len(cheq)==0:
                db.execute("INSERT INTO holdings ('userid', 'ticker', 'qty', 'value') VALUES(:uid, :tick, :qty, :val)",
                uid=session['user_id'], tick=request.form.get("TICKER"), qty=session['buytester']["qty"], val=session['buytester']["value"])        

                db.execute("INSERT INTO hist (userid, action, qty, value, ticker) VALUES(?, ?, ?, ?, ?)", session['user_id'], "buy", session['buytester']["qty"],session['buytester']["value"],request.form.get("TICKER"))

            else:
                newqty=cheq[0]['qty']+int(session['buytester']["qty"])
                avgval=(cheq[0]['qty']*cheq[0]['value']+int(session['buytester']["qty"])*session['buytester']["value"])/(newqty)
                db.execute("UPDATE holdings SET qty=:newqty, value=:avgval WHERE userid=:uid AND ticker=:tick",
                uid=session['user_id'], tick=request.form.get("TICKER"), newqty=newqty, avgval=avgval)        
    
                db.execute("INSERT INTO hist (userid, action, qty, value, ticker) VALUES(?, ?, ?, ?, ?)", session['user_id'], "buy", session['buytester']["qty"],session['buytester']["value"],request.form.get("TICKER"))

    
            #print(session['buytester']["qty"],session['buytester']["value"])
            return render_template("buy.html", bt=session["buytester"])
        else:
            return apology("NO BEANS", 69)
    else:
        return render_template("buy.html", bt=session["buytester"])


@app.route("/history")
@login_required
def history():
    
    session["hist"] = db.execute("SELECT * FROM hist WHERE userid=:uid ORDER BY time ASC", uid=session['user_id'])
    
    return render_template("hist.html", hist=session["hist"])
    
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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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

    if "tester" not in session:
        session["tester"] = []

    if request.method == "POST":
        #reqarg="https://cloud.iexapis.com/stable/stock/"+request.form.get("TICKER")+"/quote?token="+"pk_e2fa49fd66144720aa53c0237c97d915" 
        #tester=requests.get(reqarg)
        tester=lookup(request.form.get("TICKER"))
        session['tester']=(tester)
        print(type(session['tester']))
        return render_template("quote.html", tester=session["tester"])
    else:
        return render_template("quote.html", tester=session["tester"])


@app.route("/register", methods=["GET", "POST"])
def register():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
       
        pw=generate_password_hash(request.form.get("password"))
        un=request.form.get("username")
        
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 0:
            return apology("already here", 403)
        else:
            db.execute("INSERT INTO users (username, hash) VALUES(:un, :pw)", un=un, pw=pw)
        
        
        rows=db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if len(rows) == 0:
            return apology("SOMETHING WRONG", 403)
        else:    
            session["user_id"] = rows[0]["id"]
            return redirect("/index")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if "selltester" not in session:        
        session["selltester"] = {}

    if request.method == "POST":
        session['selltester']["qty"]=request.form.get("QTY")
        session['selltester']["value"]=lookup(request.form.get("TICKER"))["price"]
        session['selltester']["name"]=lookup(request.form.get("TICKER"))["name"]
        
        row = db.execute("SELECT * FROM holdings WHERE userid = :id AND ticker=:tick", id=session["user_id"], tick=request.form.get("TICKER"))
        if len(row)!=0:
            if row[0]['qty']>=int(session['selltester']["qty"]):
                cashafter=int(session['selltester']["qty"])*session['selltester']["value"]
                db.execute("UPDATE users SET cash=cash+:ca WHERE id=:uid", ca=cashafter, uid=session['user_id'])
        
                newqty=row[0]['qty']-int(session['selltester']["qty"])
                if newqty>0:
                    avgval=(row[0]['qty']*row[0]['value']-int(session['selltester']["qty"])*session['selltester']["value"])/(newqty)
                else:
                    avgval=0
                db.execute("UPDATE holdings SET qty=:newqty, value=:avgval WHERE userid=:uid AND ticker=:tick",
                uid=session['user_id'], tick=request.form.get("TICKER"), newqty=newqty, avgval=avgval)
                
                db.execute("INSERT INTO hist (userid, action, qty, value, ticker) VALUES(?, ?, ?, ?, ?)", session['user_id'], "sell", session['buytester']["qty"],session['buytester']["value"],request.form.get("TICKER"))

        
                return render_template("sell.html", st=session["selltester"])
            else:
                return apology("NOT ENOUGH EQUITY OF THIS COMPANY", 0)
        else:
            return apology("NO EQUITY OF THIS COMPANY", 0)
    else:
        return render_template("sell.html", st=session["selltester"])



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
