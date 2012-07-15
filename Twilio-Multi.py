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
        if state == 0 and request.form['Body'] == 'register': # INITIAL MESSAGE
            session['state'] = 'register'
            message = "Hola, please send me your name to continue"
        elif state == 'register':
            # GET QUESTION ONE
            # RETURN QUESTION ONE
            # TODO - CHECK LENGTH OF BODY 
            name = request.form['Body']
            g.db.execute('insert into respondents (name, phone_no) values (?, ?)',
                [name, from_number])
            g.db.commit()
            print "Inserted name and no to sqlite3"
            cur = g.db.execute('select id, question_no, text from questions where question_no = 1')
            first_q = cur.fetchone()
            message = "".join([name, ", ", first_q[2]])
            session['state'] = 1
        else: # SOMETHING WRONG - DELETE ALL EVIDENCE, RETREAT!RETREAT!!
            # DELETE ALL COOKIES
            session.clear()
            message = "Please reply with 'register' to begin.."
    else:
        #name = respondent[2]
        name = respondent[2]
        cur = g.db.execute('select count(*) from questions where survey_id = 1')
        question_count = cur.fetchone()
        print "THERE ARE %s QUESTIONS IN DB" % (question_count[0])

        current_q = session.get('state')
        cur = g.db.execute('select id, question_id from answers where respondent_id=? order by question_id asc',
            [respondent[0]])
        answers = [dict(id=row[0], question_id=row[1]) for row in cur.fetchall()]
        answer_count = len(answers)
        print "Already answered %d questions" % len(answers)

        print "Answer_count is %s and current_q is %s" % (str(answer_count), str(current_q))

        if answer_count == 0 and (current_q == 0 or current_q == None): 
            cur = g.db.execute('select id, question_no, text from questions where question_no = 1')
            first_q = cur.fetchone()
            message = "".join([name, ", ", first_q[2]])
            print "1", message
            session['state'] = 1
        elif answer_count == question_count[0]:
            print "Answered all questions - thank you!"
            message =  "Answered all questions - thank you!"
        else: 
            print "Current Q is %s" % (current_q)
            next_q = current_q + 1
            print "Next Q is %s" % (next_q)
            cur = g.db.execute('select id, question_no, text from questions where question_no = ?', 
                [current_q])
            question = cur.fetchone()
            message = "".join([name, ", ", question[2]])
            print "2", message

            session['state'] = next_q
            print "Setting state to ", next_q

            new_answer = request.form['Body']
            print "length of answer is %d" % len(new_answer)
            if answer_count == (current_q - 1) and len(new_answer) > 0:
                cur = g.db.execute('select id from questions where survey_id = 1 and question_no = ?', 
                    [current_q])
                cur_question_id = cur.fetchone()
                print "Respondent id is %s , current question id s %s and new_answer is %s)" % (respondent[0], cur_question_id, new_answer)
                g.db.execute('insert into answers (respondent_id, question_id, text) values (?, ?, ?)',
                    [respondent[0], cur_question_id[0], new_answer])
                g.db.commit()

            else:
                # COOKIES EXPIRED OR OUR OF SYNC - DELETE COOKIE, DEFER TO DB COUNT AND PROCEED
                session.clear()

            session['state'] = next_q

    to_number = request.form['To']
    resp = twilio.twiml.Response()
    resp.sms(message)

    return str(resp)

@app.route("/showquestions")
def show_questions():
    cur = g.db.execute('select id, survey_id, question_no, text from questions order by id desc')
    questions = [dict(id=row[0], survey_id=row[1],question_no=row[2], text=row[3]) for row in cur.fetchall()]
    return render_template('show_questions.html', questions=questions)

@app.route('/addquestion', methods=['POST'])
def add_question():
    g.db.execute('insert into questions (survey_id, question_no, text) values (?, ?, ?)',
                 [request.form['survey_id'], request.form['question_no'], request.form['text']])
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
