# -*- coding: utf-8 -*-
"""
@author: Steven Court
Main app for web interface using flask and sqlite3
"""

from datetime import timedelta

import sqlite3
from werkzeug.security import check_password_hash
from flask import Flask, redirect, url_for, render_template, request, session


app = Flask(__name__)
app.config["SESSION_PERMANENT"] = True
app.permanent_session_lifetime = timedelta(minutes=2)
app.secret_key = "your_key_here"


def check_password(user, password):
    """Check username and password against database
    
    db has columns "userid" and "pwd"
    Returns True/False
    """
    # Connect to sqlite3 db
    connection = sqlite3.connect("authorized_users.db")
    cursor = connection.cursor()
    # Get hashed password
    cursor.execute('''SELECT pwd FROM users WHERE userid=?''', (user,))
    data = cursor.fetchall()
    if data:
        pwd_hash = data[0][0]
        return check_password_hash(pwd_hash, password)
    else:
        return False



@app.route("/")
def index():
    if "user" in session:
        session.pop("user", None)
    return render_template("login.html")


@app.route("/home")
def home():
    if "user" in session:
        return render_template("home.html", username=session["user"])
    else:
        return redirect(url_for("login"))



@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        #session.permanent = False
        user = request.form["userid"]
        pwd_text = request.form["password"]
        
        # Check user exists and pwd correct
        if check_password(user,pwd_text): 
            session["user"] = user
            return redirect(url_for("home", username=user))
        else:
            return render_template("login.html", msg="USER ID OR PASSWORD NOT RECOGNIZED")
    else:
        if "user" in session:
            #session.clear()
            session.pop("user",None)
        return render_template("login.html")



@app.route("/submission", methods=["GET","POST"])
def submission():
    if "user" in session:
        if request.method == "POST":
            patientid = request.form["patientid"]
            plan = request.form["plan"]
            if "let" in request.form:
                let="on"
            else:
                let="off"
            if "dosetowater" in request.form:
                dosetowater="on"
            else:
                dosetowater="off"       

            return render_template("summary.html", plan=plan, patientid=patientid,
                                    let=let, dosetowater=dosetowater)
        else:
            # render page
            return render_template("submission.html")
    else:
        return redirect(url_for("login"))



@app.route("/summary")
def summary(patientid, plan, let, dosetowater):
    return render_template("summary.html")


@app.route("/help")
def help():
    return render_template("help.html")


@app.route('/logout')
def logout():
   # remove the username from the session if it is there
   if "user" in session:
       session.pop("user", None)
       #session.clear()
   return redirect(url_for("login"))
   

if __name__== "__main__":
    app.run(debug=True)
