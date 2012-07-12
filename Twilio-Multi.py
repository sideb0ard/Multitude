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
def hello_monkey():
    """Respond to incoming calls with a simple text message."""

    counter = session.get('counter', 0)
         
    # increment the counter
    counter += 1
    # Save the new counter value in the session
    session['counter'] = counter

    from_number = request.form['From']
    if from_number in callers:
        name = callers[from_number]
    else:
        name = "Monkey"

    to_number = request.form['To']

    message = "".join([name, " has messaged ", request.form['To'], " ", str(counter), " times."])
    #message = "".join([name, " has messaged ", str(counter)])

    g.db.execute('insert into respondents (name, phone_no) values (?, ?)',
                 [name, from_number])
    g.db.commit()
    print "Inserted name and no to sqlite3"
 
    resp = twilio.twiml.Response()
    resp.sms(message)

    return str(resp)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()
 
if __name__ == "__main__":
    app.run(debug=True)
