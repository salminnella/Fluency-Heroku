import os
from flask import jsonify
from flask import Flask, request
from flask import url_for
from twilio.jwt.access_token import AccessToken, VoiceGrant
from twilio.rest import Client
import twilio.twiml

ACCOUNT_SID = 'AC***'
API_KEY = 'SK***'
API_KEY_SECRET = '***'
PUSH_CREDENTIAL_SID = 'CR***'
APP_SID = 'AP***'

IDENTITY = 'voice_test'
CALLER_ID = 'quick_start'

app = Flask(__name__)

@app.route('/accessToken')
def token():
  account_sid = os.environ.get("ACCOUNT_SID", ACCOUNT_SID)
  api_key = os.environ.get("API_KEY", API_KEY)
  api_key_secret = os.environ.get("API_KEY_SECRET", API_KEY_SECRET)
  push_credential_sid = os.environ.get("PUSH_CREDENTIAL_SID", PUSH_CREDENTIAL_SID)
  app_sid = os.environ.get("APP_SID", APP_SID)

  grant = VoiceGrant(
    push_credential_sid=push_credential_sid,
    outgoing_application_sid=app_sid
  )

  token = AccessToken(account_sid, api_key, api_key_secret, IDENTITY)
  token.add_grant(grant)

  return str(token)

@app.route('/outgoing', methods=['GET', 'POST'])
def outgoing():
  try:
       twilio_client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
  except Exception as e:
      msg = 'Missing configuration variable: {0}'.format(e)
      return jsonify({'error': msg})

  try:
      twilio_client.calls.create(to=to,
                                 from_=CALLER_ID,
                                 url=url_for('.call', callType="inPerson", record="true", To="5204403178", userID="fXtYkA9NBdSN3JH9uXfI8vpYlcs1", _external=True))

  except Exception as e:
      app.logger.error(e)
      return str("Error creating client")

  return jsonify({'message': 'Call incoming!'})

@app.route('/call', methods=['GET', 'POST'])
def call():
    resp = twilio.twiml.Response()
    to = request.values.get('To')
    userID = request.values.get('userID')
    caller_id = CALLER_ID

    result = firebase.patch('/User/' + userID + '/callStatus', {'answered': 'true'})

    {u'name': u'-Io26123nDHkfybDIGl7'}
    resp = "<Response><Say loop=\"0\">_</Say></Response>"
    # resp.say("_", loop="0")

    return str(resp)

@app.route('/incoming', methods=['GET', 'POST'])
def incoming():
  resp = twilio.twiml.Response()
  resp.say("Congratulations! You have received your first inbound call! Good bye.")
  return str(resp)

@app.route('/placeCall', methods=['GET', 'POST'])
def placeCall():
  account_sid = os.environ.get("ACCOUNT_SID", ACCOUNT_SID)
  api_key = os.environ.get("API_KEY", API_KEY)
  api_key_secret = os.environ.get("API_KEY_SECRET", API_KEY_SECRET)

  client = Client(api_key, api_key_secret, account_sid)
  call = client.calls.create(url=request.url_root + 'incoming', to='client:' + IDENTITY, from_='client:' + CALLER_ID)
  return str(call.sid)

@app.route('/', methods=['GET', 'POST'])
def welcome():
  resp = twilio.twiml.Response()
  resp.say("Welcome to Twilio")
  return str(resp)

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
