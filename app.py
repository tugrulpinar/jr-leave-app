from select_menu import appeal_types_ledger, province_ledger, registry_offices_ledger
from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from helpers import apology, login_required
from pdf_recognizer import PdfRecognizer
from cryptography.fernet import Fernet
from flask_session import Session
from datetime import datetime
from tempfile import mkdtemp
from rq import Queue, Retry
from worker import conn
from jr_notice import *
from cs50 import SQL
import functools
import time
import os

# Configure application
app = Flask(__name__)
q = Queue(connection=conn)
# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///leave_app.db")


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response


app.config["FILE_PATH"] = None
app.config["CLIENT_FOLDER"] = None
app.config["CLIENT_LEDGER"] = None
app.config["APPEAL_TYPE"] = None
app.config["SECONDARY_EMAIL"] = ""
app.config["MAX_PDF_FILESIZE"] = 0.5 * 1024 * 1024
app.config["ALLOWED_FILE_EXTENSIONS"] = ["PDF"]
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_COOKIE_SECURE"] = True
# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


def allowed_image(filename):
    if not "." in filename:
        return False
    ext = filename.rsplit(".", 1)[1]
    if ext.upper() in app.config["ALLOWED_FILE_EXTENSIONS"]:
        return True
    else:
        return False


def allowed_image_filesize(filesize):
    if int(filesize) <= app.config["MAX_PDF_FILESIZE"]:
        return True
    else:
        return False


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")


@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"Server Error: {e}, route: {request.url}")
    return render_template("500.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        # result = db.execute("SELECT key FROM login_key")
        # login_key = result[0]["key"].encode()

        # f = Fernet(login_key)

        email = request.form.get("email")
        if not email:
            return apology("Please enter an email")

        temp_name = db.execute(
            "SELECT email FROM users WHERE email = ?", email)

        if temp_name:
            return apology("Email already exists")

        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not password or not confirmation:
            return apology("Please enter password")

        if password != confirmation:
            return apology("Passwords do not match")

        hash_password = generate_password_hash(password)
        user_key = Fernet.generate_key()

        db.execute("INSERT INTO users (email, password, key) VALUES (?, ?, ?)",
                   email, hash_password, user_key.decode())

        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # result = db.execute("SELECT key FROM login_key")
        # login_key = result[0]["key"].encode()

        # f = Fernet(login_key)

        # Query database for email
        rows = db.execute("SELECT * FROM users WHERE email = ?",
                          request.form.get("email"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # get the encrpytion key
        query = db.execute("SELECT key FROM users WHERE id = ?",
                           session["user_id"])

        user_key = query[0]["key"].encode()
        # remember the encryption key
        session["user_key"] = user_key

        app.config["CLIENT_FOLDER"] = os.path.join(
            os.getcwd(), "static", "client", str(session["user_id"]))

        if not os.path.exists(app.config["CLIENT_FOLDER"]):
            os.mkdir(app.config["CLIENT_FOLDER"])

        con = os.listdir(app.config["CLIENT_FOLDER"])
        if con:
            for item in con:
                file_path = os.path.join(app.config["CLIENT_FOLDER"], item)
                os.remove(file_path)

        # Redirect user to home page
        return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/filing-party-info", methods=["GET", "POST"])
@login_required
def filing_party_info():

    if request.method == "POST":

        firstname = request.form.get("firstname")
        if not firstname:
            return apology("Please enter firstname")

        lastname = request.form.get("lastname")
        if not lastname:
            return apology("Please enter lastname")

        address = request.form.get("address")
        if not address:
            return apology("Please enter address")

        city = request.form.get("city")
        if not city:
            return apology("Please enter city")

        province = request.form.get("province")
        if not province or not province in province_ledger:
            return apology("Please enter province")

        postal_code = request.form.get("postal_code")
        if not postal_code:
            return apology("Please enter postal_code")

        phone = request.form.get("phone")
        if not phone:
            return apology("Please enter phone")

        email = request.form.get("email")
        if not email:
            return apology("Please enter email")

        language = request.form.get("language")
        if not language:
            return apology("Please enter language")

        registry_office = request.form.get("registry_office")
        if not registry_office or not registry_office in registry_offices_ledger:
            return apology("Please enter registry office")

        container = [firstname, lastname, address, city, province,
                     postal_code, phone, email, language, registry_office]

        result = db.execute(
            "SELECT user_id FROM filing_party_info WHERE user_id = ?", session["user_id"])

        f = Fernet(session["user_key"])

        def encrypt(x):
            a = f.encrypt(x.encode())
            return a.decode()

        # encrypt the user information
        encrypted_container = list(map(encrypt, container))

        if not result:
            db.execute("INSERT INTO filing_party_info VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       session["user_id"], encrypted_container[0],
                       encrypted_container[1], encrypted_container[2],
                       encrypted_container[3], encrypted_container[4],
                       encrypted_container[5], encrypted_container[6],
                       encrypted_container[7], encrypted_container[8], encrypted_container[9])

        db.execute("UPDATE filing_party_info SET first_name= ?, last_name= ?, address= ?, city= ?, province= ?, \
                   postal_code= ?, phone= ?, email= ?, \
                    language= ?, registry_office= ? WHERE user_id= ?",
                   encrypted_container[0], encrypted_container[1],
                   encrypted_container[2], encrypted_container[3],
                   encrypted_container[4], encrypted_container[5],
                   encrypted_container[6], encrypted_container[7],
                   encrypted_container[8], encrypted_container[9], session["user_id"])

        time.sleep(0.6)
        return redirect("/profile")
    else:
        return render_template("filing_party_info.html")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        return redirect("/filing-party-info")

    results = db.execute(
        "SELECT * FROM filing_party_info WHERE user_id = ?", session["user_id"])

    if not results:
        return redirect("/filing-party-info")

    values = list(results[0].values())

    f = Fernet(session["user_key"])

    decrypted_container = list(
        map(lambda x: f.decrypt(x.encode()).decode(), values[1:]))

    return render_template("profile.html", results=decrypted_container)


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    results = db.execute(
        "SELECT * FROM submissions WHERE user_id = ?", session["user_id"])

    f = Fernet(session["user_key"])

    for item in results:
        item["lastname"] = f.decrypt(item["lastname"].encode()).decode()
        item["firstname"] = f.decrypt(item["firstname"].encode()).decode()
        item["appeal_type"] = f.decrypt(item["appeal_type"].encode()).decode()
        item["submission_date"] = f.decrypt(
            item["submission_date"].encode()).decode()
        item["due_date"] = f.decrypt(item["due_date"].encode()).decode()
        item["secondary_email"] = f.decrypt(
            item["secondary_email"].encode()).decode()
        item["confirmation_number"] = f.decrypt(
            item["confirmation_number"].encode()).decode()

    return render_template("index.html", results=results)


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":

        appeal_type = request.form["appeal_type"]

        # ensure the user puts a valid appeal type
        if not appeal_type or not appeal_type in appeal_types_ledger:
            return apology("Please select a valid appeal type")

        if request.files:
            if "filesize" in request.cookies:
                if not allowed_image_filesize(request.cookies["filesize"]):
                    print("Filesize exceeded maximum limit")
                    return apology("Filesize exceeded maximum limit")

                file = request.files["file"]

                if file.filename == "":
                    print("No filename")
                    return apology("No filename")

                if allowed_image(file.filename):
                    filename = secure_filename(file.filename)
                    app.config["FILE_PATH"] = os.path.join(
                        app.config["CLIENT_FOLDER"], filename)
                    file.save(app.config["FILE_PATH"])
                    print("File saved")
                else:
                    print("That file extension is not allowed")
                    return apology("That file extension is not allowed")
        else:
            return apology("Please upload a file")

        t1 = time.time()
        pdf_rec = PdfRecognizer(app.config["FILE_PATH"])
        pdf_rec.extract_fullnames()
        print(pdf_rec.ledger)
        t2 = time.time()
        time_took = round(t2-t1, 3)
        print("Time: ", t2-t1)

        db.execute("INSERT INTO meta VALUES (?,?,?)",
                   "pdf_rec", str(datetime.now()), time_took)

        app.config["CLIENT_LEDGER"] = pdf_rec.ledger
        app.config["APPEAL_TYPE"] = appeal_type

        if request.form.get("secondary_email"):
            app.config["SECONDARY_EMAIL"] = request.form.get("secondary_email")
        return redirect("/launch")

    results = db.execute(
        "SELECT * FROM filing_party_info WHERE user_id = ?", session["user_id"])

    if not results:
        return redirect("/filing-party-info")

    return render_template("upload.html")


@app.route("/launch", methods=["GET", "POST"])
@login_required
def launch():
    if request.method == "POST":

        number_of_applicants = app.config["CLIENT_LEDGER"]["number_of_applicants"]
        first_names = list(
            map(lambda x: x[0], app.config["CLIENT_LEDGER"]["app_fullname"]))
        last_names = list(
            map(lambda x: x[1], app.config["CLIENT_LEDGER"]["app_fullname"]))

        results = db.execute(
            "SELECT * FROM filing_party_info WHERE user_id = ?", session["user_id"])

        f = Fernet(session["user_key"])
        values = list(results[0].values())[1:]
        decrypted_container = list(
            map(lambda x: f.decrypt(x.encode()).decode(), values))

        try:
            efile_jr_notice(number_of_applicants, first_names, last_names,
                            app.config["APPEAL_TYPE"], decrypted_container, app.config["FILE_PATH"],
                            app.config["SECONDARY_EMAIL"], session["user_id"], session["user_key"],
                            app.config["CLIENT_FOLDER"])
        except Exception as e:
            print(e)
            return apology("Something went wrong")
        # job = q.enqueue(efile_jr_notice, number_of_applicants, first_names, last_names,
        #                 app.config["APPEAL_TYPE"], results, file_path, app.config["SECONDARY_EMAIL"], session["user_id"], retry=Retry(max=2))

        return render_template("task_confirmation.html")
    else:
        return render_template("verification.html", ledger=app.config["CLIENT_LEDGER"])


@app.route("/check", methods=["GET", "POST"])
# @login_required
@functools.lru_cache(maxsize=128)
def check():
    t1 = time.time()
    p_rec = PdfRecognizer("./static/App3.pdf")
    p_rec.extract_fullnames()
    print(p_rec.ledger)
    t2 = time.time()
    print(t2-t1)
    return redirect("/login")


@app.route("/logout")
def logout():
    """Log user out"""
    # clean everything
    con = os.listdir(app.config["CLIENT_FOLDER"])

    if con:
        for item in con:
            file_path = os.path.join(app.config["CLIENT_FOLDER"], item)
            os.remove(file_path)

    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
