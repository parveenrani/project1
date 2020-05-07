import os
import requests
from flask import Flask, render_template, flash,request, session, url_for, redirect, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
app.secret_key="secret"
engine = create_engine(os.getenv("DATABASE_URL"))

db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def home():
    if 'username' in session:
        return render_template("booksearch.html")
    return redirect(url_for('login'))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route("/login",methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if db.execute("Select username from user_detail where username=:user", {"user": username}).rowcount==0:
            flash("No username","danger")
            return render_template("login.html")
        else:
            passworddetail = db.execute("Select * from user_detail where username=:user",{"user": username}).fetchone()
            if password == passworddetail.password:
                session["userid"] = passworddetail.userid
                session["username"] = passworddetail.username
                return render_template("booksearch.html")
            else:
                flash("Incorrect password","danger")
                return render_template("login.html")
    return render_template("login.html")


@app.route("/register",methods=["GET","POST"])
def register():
    if request.method == "POST":
        user_name = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
        if user_name == "" or password1 == "" or password2 == "":
            flash("Fields required..", "error")
        else:
            if db.execute("Select * from user_detail where username=:user",{"user":user_name}).rowcount==0:
                if password1 == password2:
                    db.execute("INSERT INTO user_detail (username, password) VALUES (:username, :password)",
                               {"username": user_name, "password": password1})
                    db.commit()
                    return redirect(url_for('login'))
                else:
                    flash("Password doesn't match","danger")
                    return render_template("register.html")
            else:
                flash("That user already exist...","danger")
    return render_template("register.html")


@app.route("/booksearch", methods=["POST","GET"])
def booksearch():
    if 'username' not in session:
        return redirect(url_for("login"))
    search_opt = request.form.get("criteria")
    searchval = request.form.get("booksearch")
    if searchval=="":
        flash("No result found...","warning")
        return render_template("booksearch.html")
    elif searchval is None:
        return render_template("booksearch.html")
    else:
        searchval = searchval.lower()
        searchTitleCase = searchval.title()
        searchqry = "Select * from book_detail where {} like '%{}%' or {} like '%{}%'".format(search_opt, searchval,
                                                                                          search_opt, searchTitleCase)
        searchresults = db.execute(searchqry)
        if searchresults.rowcount==0:
            flash("No matched results","warning")
            return render_template("booksearch.html")

        return render_template("booksearch.html", searchresults=searchresults)

@app.route('/api/<string:isbn>', methods=['GET'])
def api_id(isbn):
    det = db.execute("select * from book_detail where isbn=:isbn",{"isbn":isbn})
    if det.rowcount==0:
        return "<h2>Not Found</h2>"
    return jsonify({'result': [dict(row) for row in det]})

@app.route("/booksearch/<int:bookid>",methods=["GET","POST"])
def bookdetail(bookid):
    if request.method == "POST":
        review = request.form.get("review")
        rating = request.form.get("rating")
        if db.execute("select * from bookreview where bookid=:bookid and userid=:userid",{"bookid":bookid,"userid":session["userid"]}).rowcount==0:
            db.execute("Insert into bookreview(review,rating,bookid,userid) values(:review,:rating,:bookid,:userid)",
                   {"review":review,"rating":rating,"bookid":bookid,"userid":session["userid"]})
            db.commit()
            return render_template("success.html")
        else:
            pass
    else:
        results = db.execute("Select * from book_detail where bookid = :bookid",{"bookid":bookid}).fetchone()
        reviewresult=db.execute("Select review,rating,username,bookid,bookreview.userid as userid from bookreview join user_detail " \
                                "on bookreview.userid=user_detail.userid where bookid = :bookid", \
                                {"bookid":bookid}).fetchall()

        user_count=0
        for rev in reviewresult:
            if rev.userid == session["userid"]:
                user_count +=1

        ################goodreads api#########################
        key = os.getenv("GOODREADS_KEY")
        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                           params={"key": key, "isbns": results.isbn})
        if res.status_code != 200:
            raise ValueError
        reviews_count = res.json()["books"][0]["reviews_count"]
        average_rating = res.json()["books"][0]["average_rating"]
        lstgoodreads=[reviews_count,average_rating]

        ##############################################################

        return render_template("bookdetail.html", results=results,reviewresult=reviewresult,user_count=user_count,lstgoodreads=lstgoodreads)


if __name__ == "__main__":
    app.run()

