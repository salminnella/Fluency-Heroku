import os
from flask import Flask, request
from twilio.util import TwilioCapability
from twilio.rest import TwilioRestClient
import twilio.twiml
from firebase import firebase

# Account Sid and Auth Token can be found in your account dashboard
ACCOUNT_SID = 'AC2a1860c5996ee58009cb5ea5a22d29f7'
AUTH_TOKEN = '375378e3bf5c28925a951f5ad54a0b70'

# TwiML app outgoing connections will use
APP_SID = 'AP64b440ac8f67ab9e653ebd21c9b8a2f6'

CALLER_ID = '+15204403178'
CLIENT = 'anthony'


app = Flask(__name__)

@app.route('/token')
def token():
  account_sid = os.environ.get("ACCOUNT_SID", ACCOUNT_SID)
  auth_token = os.environ.get("AUTH_TOKEN", AUTH_TOKEN)
  app_sid = os.environ.get("APP_SID", APP_SID)

  capability = TwilioCapability(account_sid, auth_token)

  # This allows outgoing connections to TwiML application
  if request.values.get('allowOutgoing') != 'false':
     capability.allow_client_outgoing(app_sid)

  # This allows incoming connections to client (if specified)
  client = request.values.get('client')
  if client != None:
    capability.allow_client_incoming(client)

  # This returns a token to use with Twilio based on the account and capabilities defined above
  return capability.generate()

@app.route('/call', methods=['GET', 'POST'])
def call():
  """ This method routes calls from/to client                  """
  """ Rules: 1. From can be either client:name or PSTN number  """
  """        2. To value specifies target. When call is coming """
  """           from PSTN, To value is ignored and call is     """
  """           routed to client named CLIENT                  """
  resp = twilio.twiml.Response()
  from_value = request.values.get('From')
  conf_name = request.values.get('ConfName')
  to = request.values.get('To')
  recordConference = request.values.get('RecordConf')
  recordCall = request.values.get('RecordCall')
  caller_id = os.environ.get("CALLER_ID", CALLER_ID)
  digits = request.values.get('SendDigits')
  
  if digits:
      output = "<Response><Dial callerId=\"5204403178\"><Number sendDigits=\"wwwwww4860\">" + to + "</Number></Dial></Response>"
      return str(output)

  if conf_name:
      resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
      return resp

  if not (from_value and to):
    resp.say("Invalid request")
    return str(resp)

  from_client = from_value.startswith('client')
  caller_id = os.environ.get("CALLER_ID", CALLER_ID)

  if not from_client:
    # PSTN -> client
    resp.dial(callerId=from_value).client(CLIENT)
  elif to.startswith("client:"):
    # client -> client
    resp.dial(callerId=from_value).client(to[7:])
  elif to.startswith("conference:"):
    # client -> conference
    if recordConference:
        resp = "<Response><Dial><Conference record=\"record-from-start\" eventCallbackUrl=\"https://fluency-1.herokuapp.com/confRecordings\">" + to[11:] + "</Conference></Dial></Response>"
    else:
        resp = "<Response><Dial><Conference>" + to[11:] + "</Conference></Dial></Response>"
  else:
    # client -> PSTN
    if recordCall:
        resp = "<Response><Dial record-from-answer=\"true\" action=\"https://fluency-1.herokuapp.com/callRecordings\" method=\"POST\">" + to + "</Dial></Response>"
    else:
        resp.dial(to, callerId=caller_id)

  return str(resp)

@app.route('/join', methods=['GET', 'POST'])
def join():
    conf_name = request.values.get('ConfName')
    to = request.values.get('To')
    twilioClient = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
    
    call = twilioClient.calls.create(url="https://fluency-1.herokuapp.com/call?ConfName=" + conf_name,
                           to = request.values.get('To'),
                           from_="+15204403178"
                           )
    
    resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
    return str(resp)

@app.route('/confRecordings', methods=['GET', 'POST'])
def confRecordings():

    # Recording list from twilio 1
    # A list of recording objects with the properties described above
    #twilioClient = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
    #recordings = twilioClient.recordings.list(CallSid=call.sid)
    #for recording in twilioClient.recordings.list():
    #print recording.duration
    #CallSid = "CAd3e777bd7c010db188fb0c8d722339eb"

    #Recording list from twilio 2
    #twilioClient = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
    #recordings = twilioClient.recordings.list(date_created="2016-08-02")
    #recordings = twilioClient.recordings.list()
    #return recordings[0]
    #twilioClient.recordings.delete("REe803d46f4a94d8350e66323f0e5ebceb")


    recordingLink = request.values.get('RecordingUrl')
    recordingDuration = request.values.get('Duration')
    recordingTimestamp = request.values.get('timestamp')
    recordingCallSid = request.values.get('CallSid')

    #Ozgur - firebase push -- working
    global firebase
    firebase = firebase.FirebaseApplication('https://project-5176964787746948725.firebaseio.com')
    new_user = 'OzgurVatansever2233'
    result = firebase.put('/User/Anthonyminnella/callHistory', new_user, data={'whatever': recordingLink})
    print result
    {u'name': u'-Io26123nDHkfybDIGl7'}

    return str(recordingLink)

@app.route('/callRecordings', methods=['GET', 'POST'])
def callRecordings():
    
    callSid = request.values.get('DialCallSid')
    callDuration = request.values.get('DialCallDuration')
    recordingLink = request.values.get('RecordingUrl')
    
    #Ozgur - firebase push -- working
    global firebase
    firebase = firebase.FirebaseApplication('https://project-5176964787746948725.firebaseio.com')
    new_user = 'OzgurVatansever2255'
    result = firebase.put('/User/Anthonyminnella/callHistory', new_user, data={'whatever': recordingLink})
    print result
    {u'name': u'-Io26123nDHkfybDIGl7'}
    
    return str(recordingLink)

@app.route('/', methods=['GET', 'POST'])
def welcome():
  resp = twilio.twiml.Response()
  resp.say("Welcome to Twilio")
  return str(resp)

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
