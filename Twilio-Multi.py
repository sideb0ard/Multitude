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
        # RESPONDENT IS NEW SO WE REGISTER 
        state = session.get('state',0)
        if state == 0 and request.form['Body'] == 'register': # INITIAL MESSAGE
            print "Register request received from %s" % (from_number)
            session['state'] = 'register'
            message = "Hola, please send me your name to continue"
        elif state == 'register' and len(request.form['Body']) > 0:
            # SAVE NAME TO DB
            name = request.form['Body']
            g.db.execute('insert into respondents (name, phone_no) values (?, ?)',
                [name, from_number])
            g.db.commit()
            print "Inserted name and no to sqlite3"
            #REPLY WITH FIRST QUESTION AND SET COOKIE STATE = QUESTION_NO
            cur = g.db.execute('select id, question_no, text from questions where question_no = 1')
            first_q = cur.fetchone()
            message = "".join([name, ", ", first_q[2]])
            session['state'] = 1
        else: # SOMETHING WRONG - DELETE ALL EVIDENCE, RETREAT!RETREAT!!
            # DELETE ALL COOKIES
            print "Initial request received from %s" % (from_number)
            session.clear()
            message = "Please reply with 'register' to begin.."
    else:
        # WE KNOW RESPONDENT HAS REGISTERED SO WORK OUT WHAT IS NEXT QUESTION TO SEND
        name = respondent[2]
        cur = g.db.execute('select count(*) from questions where survey_id = 1')
        question_count = cur.fetchone() # WE USE THIS TO COMPARE WITH ANSWERED COUNT TO SEE IF WE'RE DONE
        print "THERE ARE %s QUESTIONS IN DB" % (question_count[0])

        cur = g.db.execute('select id, question_id from answers where respondent_id=? order by question_id asc',
            [respondent[0]])
        answers = [dict(id=row[0], question_id=row[1]) for row in cur.fetchall()]
        print "Already answered %d questions" % len(answers)
        answer_count = len(answers)
        current_q = session.get('state')
        print "Answer_count is %s and current_q is %s" % (str(answer_count), str(current_q))

        if answer_count == 0 and (current_q == 0 or current_q == None): 
            # RESPONDENT HAS NOT ANSWERED ANY SO START FROM BEGIN
            cur = g.db.execute('select id, question_no, text from questions where question_no = 1')
            first_q = cur.fetchone()
            message = "".join([name, ", ", first_q[2]])
            print "1", message
            session['state'] = 1
        elif answer_count == question_count[0]:
            print "Answered all questions - thank you!"
            message =  "Answered all questions - thank you!"
        else: 
            # SEE IF OUR BODY HAS AN ANSWER RESPONSE
            new_answer = request.form['Body']
            print "length of answer is %d" % len(new_answer)
            print "CURRENTQ is %s" % ([current_q])
            if answer_count > 0 and (current_q == 0 or current_q == None):
                # COOKIES COUNT DOESNT MATCH SO LETS RESEND LAST QUESTION AND RESYNC COOKIES
                print "Cookies don't match, so just pick up after last answered question"
                cur = g.db.execute('select id, question_no, text from questions where question_no = ?', 
                    [answer_count + 1])
                question = cur.fetchone()
                message = "".join(["QUESTION: ", str(question[1]), " ", question[2]])
                print message
                session['state'] = answer_count + 1
                print "Setting state to ", answer_count + 1
            elif current_q == (answer_count + 1) and len(new_answer) > 0: # IE ANSWER COUNT AND COOKIE COUNT BOTH MATCH AND ANSWER NOT EMPTY
                # SAVE CURRENT ANSWER
                cur = g.db.execute('select id from questions where survey_id = 1 and question_no = ?', 
                    [current_q])
                cur_question_id = cur.fetchone()
                print "Respondent id is %s , current question id s %s and new_answer is %s)" % (respondent[0], cur_question_id, new_answer)
                g.db.execute('insert into answers (respondent_id, question_id, text) values (?, ?, ?)',
                    [respondent[0], cur_question_id[0], new_answer])
                g.db.commit()

                # GET NEXT QUESTION OF SEND THANK YOU IF FINISHED
                print "Current Q is %s" % (current_q)
                next_q = current_q + 1
                print "Next Q is %s" % (next_q)
                if next_q > question_count[0]:
                    message = "You have now answered all questions - thank you very much"
                    session.clear()
                else:
                    cur = g.db.execute('select id, question_no, text from questions where question_no = ?', 
                        [next_q])
                    question = cur.fetchone()
                    message = "".join(["QUESTION: ", str(question[1]), " ", question[2]])
                    print message
                    session['state'] = next_q
                    print "Setting state to ", next_q

            else:
                # COOKIES EXPIRED OR OUR OF SYNC - DELETE COOKIE, DEFER TO DB COUNT AND PROCEED
                session.clear()
                message = "reset>>"


    to_number = request.form['To']
    resp = twilio.twiml.Response()
    resp.sms(message)

    return str(resp)

@app.route("/questions")
def show_questions():
    cur = g.db.execute('select id, survey_id, question_no, text from questions order by id asc')
    questions = [dict(id=row[0], survey_id=row[1],question_no=row[2], text=row[3]) for row in cur.fetchall()]
    return render_template('show_questions.html', questions=questions)

@app.route("/question", methods=['POST'])
def add_question():
    g.db.execute('insert into questions (survey_id, question_no, text) values (?, ?, ?)',
                 [1, request.form['question_no'], request.form['text']])
    g.db.commit()
    flash('New question was successfully added')
    return redirect(url_for('show_questions'))

@app.route("/clear_questions")
def clear_questions():
    g.db.execute('delete from questions')
    g.db.commit()
    flash('All questions cleared')
    return redirect(url_for('show_questions'))

@app.route("/clear_respondents")
def clear_respondents():
    g.db.execute('delete from respondents')
    g.db.commit()
    flash('All respondents cleared')
    return redirect(url_for('show_respondents'))

@app.route("/clear_answers")
def clear_answers():
    g.db.execute('delete from answers')
    g.db.commit()
    flash('All answers cleared')
    return redirect(url_for('show_answers'))

@app.route("/surveys")
def show_surveys():
    cur = g.db.execute('select id, title, by id desc')
    surveys = [dict(id=row[0], title=row[1]) for row in cur.fetchall()]
    return render_template('show_surveys.html', surveys=surveys)

@app.route("/respondents")
def show_respondents():
    cur = g.db.execute('select id, name, phone_no from respondents order by id desc')
    respondents = [dict(id=row[0], name=row[1], phone_no=row[2]) for row in cur.fetchall()]
    return render_template('show_respondents.html', respondents=respondents)

@app.route("/answers")
def show_answers():
    cur = g.db.execute('select r.name, q.question_no, a.text from respondents r join answers a on r.id=a.respondent_id join questions q on q.id=a.question_id order by respondent_id, question_id')
    answers = [dict(respondent_name=row[0], question_no=row[1], text=row[2]) for row in cur.fetchall()]
    return render_template('show_answers.html', answers=answers)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()
 
if __name__ == "__main__":
    app.run(debug=True)
