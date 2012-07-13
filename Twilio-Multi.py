import sqlite3
import twilio.twiml
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash

# configuration
DATABASE = 'multitude_data.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'
 
# The session object makes use of a secret key.
SECRET_KEY = 'a secret key'
app = Flask(__name__)
app.config.from_object(__name__)

# Try adding your own number to this list!
callers = {
    "4157455030": "The B0ardside",
    "+14158675310": "Boots",
    "+14158675311": "Virgil",
}

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()
 
@app.route("/", methods=['GET', 'POST'])
def mr_question():
    """Main body - take SMS message, query/update db and respond"""

    from_number = request.form['From']

    cursor=g.db.cursor()
    cursor.execute('SELECT id,phone_no,name FROM respondents WHERE phone_no=? LIMIT 1', [from_number])
    respondent=cursor.fetchone()
    if respondent is None:
        state = session.get('state',0)
        if state == 0: # INITIAL MESSAGE
            session['state'] = 'register'
            message = "Hola, please send me your name to continue"
        elif state == 'register':
            #  CHECK FOR MESSAGE AND USE AS NAME
            # inset name
            # GET QUESTION ONE
            # RETURN QUESTION ONE
            name = request.form['Body']
            message = "hey ".join([name, ", QUESTION ONE"])
            session['state'] = 1
        else: # SOMETHING WRONG - DELETE ALL EVIDENCE, RETREAT!RETREAT!!
            # DELETE ALL COOKIES
            print "State follows.."
            print ", ".join(state)
            session['state'] = []
            message = "something FUCKED UP! deleting all cookies.."
    else:
        #name = respondent[2]
        name = respondent[2]
        current_q = session.get('state',0)
        # ERROR CHECK - GRAB LATEST QUESTION FOR THIS RESPONDENT FROM DB AND COMPARE WITH COOKIE
        # GET REPLY - CHECK NOT NULL
        # UPDATE ANSWERS WITH CURRENT_Q AND TEXT
        # GET NEXT QUESTION CURRENT_Q += 1
        current_q += 1
        # Save the new counter value in the session
        session['current_q'] = current_q

        message = "hey ".join([name, " your're on question", str(current_q)])
        print message

    to_number = request.form['To']

    #message = "".join([name, " has messaged ", str(counter)])

    #g.db.execute('insert into respondents (name, phone_no) values (?, ?)',
    #             [name, from_number])
    #g.db.commit()
    #print "Inserted name and no to sqlite3"
 
    resp = twilio.twiml.Response()
    resp.sms(message)

    return str(resp)

@app.route("/showquestions")
def show_questions():
    cur = g.db.execute('select id, survey_id, question_number, text from questions order by id desc')
    questions = [dict(id=row[0], survey_id=row[1],question_number=row[2], text=row[3]) for row in cur.fetchall()]
    return render_template('show_questions.html', questions=questions)

@app.route('/addquestion', methods=['POST'])
def add_question():
    g.db.execute('insert into questions (survey_id, question_number, text) values (?, ?, ?)',
                 [request.form['survey_id'], request.form['question_number'], request.form['text']])
    g.db.commit()
    flash('New question was successfully added')
    return redirect(url_for('show_questions'))

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()
 
if __name__ == "__main__":
    app.run(debug=True)
