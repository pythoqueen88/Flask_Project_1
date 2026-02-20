from datetime import date
import os
from urllib import response
from django import db
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from matplotlib.widgets import Cursor    
import mysql.connector
import matplotlib.pyplot as plt
import io, base64
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from flask import send_file
import pdfplumber
import random
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
app = Flask(__name__, static_folder="static")
from werkzeug.utils import secure_filename
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
import random
import io
from werkzeug.utils import secure_filename
UPLOAD_FOLDER = "static/uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
from google.genai.errors import ClientError
import base64
from google import genai

client = genai.Client(api_key="AIzaSyA-1MLMYifV3Mn9r0ziaVL7eFcaFAeJM98")

app.secret_key = "secret123"
app.secret_key = "notes-secret-key"


# ---------- MYSQL DATABASE CONNECTION ----------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",   # XAMPP default
        database="finances"
    )

# ------from flask import request
@app.route('/auth-welcome')
def auth_welcome():
    session.clear()  
    return render_template('auth_welcome.html')

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('auth_welcome'))
    return render_template('home.html')

# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (fullname, email, phone, password) VALUES (%s, %s, %s, %s)",
            (fullname, email, phone, password)
        )
        conn.commit()
        conn.close()

        flash("Registered successfully 🎉 Please login", "success")

        return redirect(url_for('login'))

    return render_template('register.html')


# ---------- LOGIN ----------
@app.route('/login', methods=['GET','POST'])
def login():
    if 'user' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cur.fetchone()
        conn.close()

        if user:

            session['user'] = user['email']
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password", "error")

    return render_template('login.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth_welcome'))


    
@app.route('/finance')
def finance():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('finance.html')

# ---------- ADD EXPENSE ----------
@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        category = request.form['category']
        amount = request.form['amount']
        payment_mode = request.form['payment_mode']
        expense_date = request.form['expense_date']
        description = request.form['description']

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO expenses
            (user_email, category, amount, payment_mode, expense_date, description)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            session['user'],
            category,
            amount,
            payment_mode,
            expense_date,
            description
        ))

        conn.commit()
        conn.close()

        flash("Expense added successfully!")
        return redirect(url_for('add_expense'))

    return render_template('add_expense.html')


# ---------- REPORT ----------
@app.route('/report', methods=['GET', 'POST'])
def report():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    # =========================
    # Month dropdown
    # =========================
    cur.execute("""
        SELECT DISTINCT DATE_FORMAT(expense_date, '%Y-%m')
        FROM expenses
        WHERE user_email=%s
        ORDER BY 1 DESC
    """, (session['user'],))
    months = [row[0] for row in cur.fetchall()]

    selected_month = request.form.get('month')

    # =========================
    # Expenses list
    # =========================
    if selected_month:
        cur.execute("""
            SELECT id, category, amount, payment_mode, expense_date, description
            FROM expenses
            WHERE user_email=%s
            AND DATE_FORMAT(expense_date, '%Y-%m')=%s
        """, (session['user'], selected_month))
    else:
        cur.execute("""
            SELECT id, category, amount, payment_mode, expense_date, description
            FROM expenses
            WHERE user_email=%s
        """, (session['user'],))

    expenses = cur.fetchall()

    # =========================
    # Category summary (IMPORTANT)
    # =========================
    if selected_month:
        cur.execute("""
            SELECT category, SUM(amount)
            FROM expenses
            WHERE user_email=%s
            AND DATE_FORMAT(expense_date, '%Y-%m')=%s
            GROUP BY category
        """, (session['user'], selected_month))
    else:
        cur.execute("""
            SELECT category, SUM(amount)
            FROM expenses
            WHERE user_email=%s
            GROUP BY category
        """, (session['user'],))

    data = cur.fetchall()

    categories = [row[0] for row in data]
    amounts = [float(row[1]) for row in data]
    total = sum(amounts)

    conn.close()

    return render_template(
        'report.html',
        expenses=expenses,
        categories=categories,
        amounts=amounts,
        total=total,
        months=months,
        selected_month=selected_month
    )


@app.route('/download_report', methods=['POST'])
def download_report():
    if 'user' not in session:
        return redirect(url_for('login'))

    selected_month = request.form.get('month')

    conn = get_db_connection()
    cur = conn.cursor()

    if selected_month:
        cur.execute("""
            SELECT id, category, amount, payment_mode, expense_date, description
            FROM expenses
            WHERE DATE_FORMAT(expense_date, '%Y-%m') = %s
            ORDER BY expense_date
        """, (selected_month,))
    else:
        cur.execute("""
            SELECT id, category, amount, payment_mode, expense_date, description
            FROM expenses
            ORDER BY expense_date
        """)

    expenses = cur.fetchall()
    conn.close()

    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(
        f"Expense Report ({selected_month if selected_month else 'All'})",
        styles['Title']
    ))

    table_data = [["S.No", "Category", "Amount", "Payment", "Date", "Description"]]

    total = 0
    for i, e in enumerate(expenses, start=1):
        amount = float(e[2])   # ✅ FIXED INDEX
        total += amount

        table_data.append([
            i,
            e[1],               # category
            f"₹{amount}",
            e[3],               # payment
            str(e[4]),           # date
            e[5]                # description
        ])

    table_data.append(["", "", "", "", "Total", f"₹{total}"])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold')
    ]))

    elements.append(table)
    pdf.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Expense_Report_{selected_month}.pdf",
        mimetype='application/pdf'
    )

# ---------- GRAPH ----------
@app.route('/graph', methods=['GET', 'POST'])
def graph():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # ===============================
    # 🔹 categories (USER SAFE)
    # ===============================
    cursor.execute("""
        SELECT DISTINCT category
        FROM expenses
        WHERE user_email=%s
    """, (session['user'],))

    categories = [row[0] for row in cursor.fetchall()]

    selected_category = None
    graph_url = None
    total_amount = 0


    # =========================================
    # 🔹 POST → CATEGORY LINE GRAPH (FIXED)
    # =========================================
    if request.method == 'POST':

        selected_category = request.form.get('category')

        cursor.execute("""
            SELECT expense_date, amount
            FROM expenses
            WHERE user_email=%s
            AND TRIM(LOWER(category)) = TRIM(LOWER(%s))
            ORDER BY expense_date
        """, (session['user'], selected_category))

        data = cursor.fetchall()

        if data:

            dates = [str(row[0]) for row in data]
            amounts = [float(row[1]) for row in data]
            total_amount = sum(amounts)

            plt.figure(figsize=(8,5))
            plt.plot(dates, amounts, marker='o', linewidth=2.5)

            for i in range(len(amounts)):
                plt.text(i, amounts[i], f"₹{amounts[i]}", ha='center')

            plt.title(f"{selected_category} Expense Trend")
            plt.xlabel("Date")
            plt.ylabel("Amount")
            plt.xticks(rotation=45)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            graph_url = base64.b64encode(buf.getvalue()).decode()
            plt.close()


    # =========================================
    # 🔹 GET → BAR GRAPH (FIXED)
    # =========================================
    else:

        cursor.execute("""
            SELECT category, SUM(amount)
            FROM expenses
            WHERE user_email=%s
            GROUP BY category
        """, (session['user'],))

        data = cursor.fetchall()

        if data:

            cats = [row[0] for row in data]
            amts = [float(row[1]) for row in data]
            total_amount = sum(amts)

            plt.figure(figsize=(7,4))
            plt.bar(cats, amts)
            plt.xticks(rotation=30)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            graph_url = base64.b64encode(buf.getvalue()).decode()
            plt.close()


    conn.close()

    return render_template(
        'graph.html',
        categories=categories,
        selected_category=selected_category,
        graph_url=graph_url,
        total_amount=total_amount
    )

@app.route('/study')
def study_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('study_dashboard.html')

@app.route('/study/notes')
def notes_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('study_notes_dashboard.html')

@app.route('/study/notes/add', methods=['GET', 'POST'])
def add_notes():

    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":

        note_date = request.form['note_date']
        note_type = request.form['note_type']
        subject = request.form['subject']
        unit = request.form['unit']
        topic_name = request.form['topic_name']
        content = request.form['content']

        file = request.files.get('file')   # safer
        filename = None

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO notes 
            (user_email, note_date, note_type, subject, unit, topic_name, content, file_name)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            session['user'],
            note_date,
            note_type,
            subject,
            unit,
            topic_name,
            content,
            filename
        ))

        conn.commit()   # 🔥 MUST
        conn.close()

        flash("Note Added Successfully!")
        return redirect("/study/notes/add")

    return render_template("notes_add.html")



@app.route('/study/notes/view')
def notes_view():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM notes WHERE user_email=%s", (session['user'],))
    notes = cur.fetchall()
    conn.close()

    return render_template('notes_view.html', notes=notes)

@app.route("/delete_study_note/<int:id>", methods=['POST'])
def delete_study_note(id):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM notes WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    return "", 204


@app.route('/study/notes/analytics')
def notes_analytics():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    # Subject wise
    cur.execute("""
        SELECT subject, COUNT(*)
        FROM notes
        WHERE user_email=%s
        GROUP BY subject
    """, (session['user'],))
    subject_data = cur.fetchall()

    subjects = [r[0] for r in subject_data]
    subject_counts = [r[1] for r in subject_data]


    # Type wise
    cur.execute("""
        SELECT note_type, COUNT(*)
        FROM notes
        WHERE user_email=%s
        GROUP BY note_type
    """, (session['user'],))
    type_data = cur.fetchall()

    types = [r[0] for r in type_data]
    type_counts = [r[1] for r in type_data]


    # Month wise
    cur.execute("""
        SELECT DATE_FORMAT(note_date,'%b %Y'), COUNT(*)
        FROM notes
        WHERE user_email=%s
        GROUP BY DATE_FORMAT(note_date,'%Y-%m')
        ORDER BY DATE_FORMAT(note_date,'%Y-%m')
    """, (session['user'],))
    month_data = cur.fetchall()

    months = [r[0] for r in month_data]
    month_counts = [r[1] for r in month_data]


    # Total notes
    total_notes = sum(subject_counts)

    conn.close()

    return render_template(
        "notes_analytics.html",
        subjects=subjects,
        subject_counts=subject_counts,
        types=types,
        type_counts=type_counts,
        months=months,
        month_counts=month_counts,
        total_notes=total_notes
    )

@app.route('/auto_notes', methods=['GET','POST'])
def auto_notes():

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    notes_text = ""
    history = []
    message = ""

    if request.method == 'POST':

        topic = request.form.get('topic', "")
        file = request.files.get('file')
        image = request.files.get('image')

        extra_text = ""
        parts = []


        # ===== PROMPT TEXT =====
        instruction = ""
        topic_lower = topic.lower()

        if "diagram" in topic_lower:
            instruction += "\nInclude a clear text diagram or flowchart."

        if "long" in topic_lower or "detailed" in topic_lower:
            instruction += "\nWrite detailed long answer with explanation."
        else:
            instruction += "\nWrite short easy student notes."

        parts.append({
            "text": f"""
Topic: {topic}

{instruction}

Extra info:
{extra_text}
"""
        })


        # ===== AI CALL SAFE =====
        try:
            response = client.models.generate_content(
                model="models/gemini-2.5-flash",
                contents=[{
                    "role": "user",
                    "parts": parts
                }]
            )

            notes_text = response.text

            # ===== SAVE HISTORY =====
            cur.execute("""
                INSERT INTO notes_history(email, topic, notes)
                VALUES (%s,%s,%s)
            """, (session['user'], topic, notes_text))
            conn.commit()



        # 🔴 QUOTA ERROR
        except ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                message = "⚠️ Your daily AI limit has expired. Try again after 24 hours."
            else:
                message = "⚠️ AI service unavailable."

        # 🔴 ANY OTHER ERROR
        except Exception as e:
            message = "⚠️ Something went wrong."
            print(e)


    # ===== LOAD HISTORY ALWAYS =====
    cur.execute("""
        SELECT * FROM notes_history
        WHERE email=%s
        ORDER BY id DESC
    """,(session['user'],))

    history = cur.fetchall()
    conn.close()

    return render_template(
        "auto_notes.html",
        notes=notes_text,
        history=history,
        message=message
    )


@app.route('/delete_note/<int:id>')
def delete_note(id):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM notes_history WHERE id=%s AND email=%s",
        (id, session['user'])
    )

    conn.commit()
    conn.close()

    return '', 204


@app.route('/timetable')
def timetable():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, course_name FROM courses")
    courses = cur.fetchall()

    conn.close()

    return render_template("timetable.html", courses=courses)


# -------- branches ----------
@app.route('/get_branches/<course_id>')
def get_branches(course_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, branch_name FROM branches WHERE course_id=%s", (course_id,))
    data = cur.fetchall()
    conn.close()
    return jsonify(data)


# -------- classes/sem ----------
@app.route('/get_classes/<branch_id>')
def get_classes(branch_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, class_name FROM classes WHERE branch_id=%s", (branch_id,))
    data = cur.fetchall()
    conn.close()
    return jsonify(data)



@app.route('/generate_timetable', methods=['POST'])
def generate_timetable():

    class_id = request.form['class_id']

    conn = get_db_connection()
    cur = conn.cursor()

    # get subjects
    cur.execute("SELECT subject_name FROM subjects WHERE class_id=%s", (class_id,))
    subjects = [s[0] for s in cur.fetchall()]

    if not subjects:
        flash("Add subjects first!")
        return redirect('/timetable')

    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    time_slots = [
        "6-7am","8-9am","5-6pm","6-7pm",
        
        "9-10pm","10-11pm",
    ]

    periods = 6

    # 🔴 IMPORTANT → old delete
    cur.execute("DELETE FROM timetables WHERE class_id=%s", (class_id,))

    # 🔵 SAVE INTO DATABASE
    for day in days:

        daily = random.sample(subjects, min(len(subjects), periods))

        while len(daily) < periods:
            daily.append(random.choice(subjects))

        cur.execute("""
            INSERT INTO timetables
            (class_id, day, period1, period2, period3, period4, period5, period6)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (class_id, day, *daily))

    conn.commit()

    # 🔵 NOW FETCH AGAIN FOR SHOW
    cur.execute("""
        SELECT day, period1, period2, period3, period4, period5, period6
        FROM timetables
        WHERE class_id=%s
        ORDER BY FIELD(day,'Mon','Tue','Wed','Thu','Fri','Sat','Sun')
    """, (class_id,))

    rows = cur.fetchall()
    conn.close()

    timetable = []

    for r in rows:
        subs = list(r[1:])
        timetable.append((r[0], subs))

    return render_template(
        "view_timetable.html",
        timetable=timetable,
        slots=time_slots
    )

@app.route("/fun_focus")
def fun_focus():
    if 'user' not in session:
        return redirect("/login")
    return render_template("fun_focus.html")
@app.route("/game")
def game():
    if 'user' not in session:
        return redirect("/login")
    return render_template("game.html")



# ================= SAVE SCORE =================
@app.route("/save_score", methods=["POST"])
def save_score():

    if "user" not in session:
        return jsonify({"ok": False, "msg": "no session"})

    data = request.get_json()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
INSERT INTO scores(username, score, time_taken, accuracy, level)
VALUES(%s,%s,%s,%s,%s)
""", (
    session["user"],
    data["score"],
    data["time"],
    data["accuracy"],
    data["level"]
))


    conn.commit()

    print("SAVED FOR:", session["user"])  # debug

    cur.close()
    conn.close()

    return jsonify({"ok": True})


# ================= PROFILE =================
@app.route("/profile")
def profile():

    if "user" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT
            IFNULL(SUM(score),0) AS total,
            COUNT(*) AS games,
            IFNULL(MAX(score),0) AS best,
            IFNULL(AVG(accuracy),0) AS acc
        FROM scores
        WHERE username=%s
    """, (session["user"],))

    r = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "profile.html",
        user=session["user"],
        total=r["total"],
        games=r["games"],
        best=r["best"],
        acc=round(r["acc"], 1)
    )



@app.route("/leaderboard")
def leaderboard():

    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # ✅ directly scores table se leaderboard
    cur.execute("""
        SELECT
            username,
            SUM(CASE WHEN level='easy' THEN score ELSE 0 END) AS easy,
            SUM(CASE WHEN level='medium' THEN score ELSE 0 END) AS medium,
            SUM(CASE WHEN level='hard' THEN score ELSE 0 END) AS hard,
            SUM(CASE WHEN level='pro' THEN score ELSE 0 END) AS pro,
            SUM(score) AS total
        FROM scores
        GROUP BY username
        ORDER BY total DESC
        LIMIT 10
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("leaderboard.html", data=data)



@app.route("/history")
def history():

    if "user" not in session:
        return redirect("/")

    email = session["user"]   # ⭐ IMPORTANT

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT level,
               score,
               time_taken,
               accuracy,
               played_at
        FROM scores
        WHERE username = %s
        ORDER BY played_at DESC
    """, (email,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("history.html", games=rows)

@app.route("/help")
def help_page():
    if "user" not in session:
        return redirect("/")  # redirect to login if not logged in
    return render_template("help.html")

@app.route("/motivational")
def motivational():

    # login check
    if "user" not in session:
        return redirect("/")   # login page

    return render_template("motivational.html")



if __name__ == '__main__':

    app.run(debug=True) 
