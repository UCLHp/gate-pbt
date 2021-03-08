# -*- coding: utf-8 -*-
"""
@author: Steven Court
Main app for web interface using flask 
"""

from flask import Flask, redirect, url_for, render_template, request



app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/submission", methods=["POST", "GET"])
def submission():
    if request.method == "POST":
        patientid = request.form["patientid"]
        plan = request.form["plan"]
        # Cannot request if unchecked!
        #let = request.form["let"]
        #dosetowater = request.form["dosetowater"]
        try:
            let = request.form["let"]
        except:
            let = "off"
        try:
            dosetowater = request.form["dosetowater"]
        except:
            dosetowater="off"       

        return render_template("summary.html", plan=plan, patientid=patientid,
                                let=let, dosetowater=dosetowater)
    else:
        # render page
        return render_template("submission.html")


@app.route("/summary")
def summary(patientid, plan, let, dosetowater):
    return render_template("summary.html")


@app.route("/help")
def help():
    return render_template("help.html")




if __name__== "__main__":
    app.run(debug=True)
