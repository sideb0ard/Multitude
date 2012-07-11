from flask import Flask, request, redirect, session
import twilio.twiml
 
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
 
    resp = twilio.twiml.Response()
    resp.sms(message)

    return str(resp)
 
if __name__ == "__main__":
    app.run(debug=True)
