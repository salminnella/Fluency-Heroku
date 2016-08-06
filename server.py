import os
from flask import Flask, request
from twilio.util import TwilioCapability
from twilio.rest import TwilioRestClient
import twilio.twiml
from firebase import firebase

# Account Sid and Auth Token can be found in your account dashboard
ACCOUNT_SID = 'AC2a1860c5996ee58009cb5ea5a22d29f7'
AUTH_TOKEN = '375378e3bf5c28925a951f5ad54a0b70'
    
global firebase
firebase = firebase.FirebaseApplication('https://project-5176964787746948725.firebaseio.com')


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
  global callType
  callType = request.values.get('callType')
  global language
  language = request.values.get('language')
  global name
  name = request.values.get('name')
  global number
  number = request.values.get('number')
  global callDateTime
  callDateTime = request.values.get('CallDateTime')
  
  resp = twilio.twiml.Response()
  from_value = request.values.get('From')
  conf_name = request.values.get('ConfName')
  to = request.values.get('To')
  recordConference = request.values.get('RecordConf')
  recordCall = request.values.get('RecordCall')
  caller_id = os.environ.get("CALLER_ID", CALLER_ID)
  digits = request.values.get('SendDigits')
  

  if digits:
      output = "<Response><Dial callerId=\"" + caller_id + "\"><Number sendDigits=\"wwwwww4860\">" + to + "</Number></Dial></Response>"
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
        resp = "<Response><Dial><Conference record=\"record-from-start\" eventCallbackUrl=\"https://fluency-1.herokuapp.com/pushRecordedConfHistory\">" + to[11:] + "</Conference></Dial></Response>"
    else:
        resp = "<Response><Dial><Conference statusCallback=\"https://fluency-1.herokuapp.com/pushConfHistory\" statusCallbackEvent=\"end\">" + to[11:] + "</Conference></Dial></Response>"
  else:
    # client -> PSTN
    if recordCall:
        resp = "<Response><Dial record=\"true\" callerId=\"" + caller_id + "\" action=\"https://fluency-1.herokuapp.com/pushRecordedCallHistory\" method=\"POST\">" + to + "</Dial></Response>"
    else:
        #resp.dial(to, callerId=caller_id)
        resp = "<Response><Dial callerId=\"" + caller_id + "\" action=\"https://fluency-1.herokuapp.com/pushCallHistory\" method=\"POST\">" + to + "</Dial></Response>"

  return str(resp)

@app.route('/conference', methods=['GET', 'POST'])
def conference():
    
    conf_name = request.values.get('ConfName')
    
    if conf_name:
        resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
        return resp


@app.route('/join', methods=['GET', 'POST'])
def join():
    conf_name = request.values.get('ConfName')
    to = request.values.get('To')
    twilioClient = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
    
    call = twilioClient.calls.create(url="https://fluency-1.herokuapp.com/conference?ConfName=" + conf_name,
                           to = request.values.get('To'),
                           from_="+15204403178"
                           )
    
    resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
    return str(resp)

@app.route('/pushCallHistory', methods=['GET', 'POST'])
def pushCallHistory():
    
    #one call to interpreter - Face to face - also returns with recordingUrl as above
    new_callHistoryID = 'OzgurVatansever401'
    callSid = request.values.get('DialCallSid')
    callDuration = request.values.get('DialCallDuration')

    #Ozgur - firebase push -- working
    result = firebase.put('/User/Anthonyminnella/callHistory', new_callHistoryID, data={'callType': callType, 'callDuration': callDuration, 'callSid': callSid, 'callDateTime': callDateTime, 'number': number, 'name': name, 'language': language})
    print result
    {u'name': u'-Io26123nDHkfybDIGl7'}

    return str(recordingUrl)

@app.route('/pushRecordedCallHistory', methods=['GET', 'POST'])
def pushRecordedCallHistory():
    
    #one call to interpreter - Face to face - also returns with recordingUrl as above
    new_callHistoryID = 'OzgurVatansever405'
    callSid = request.values.get('DialCallSid')
    callDuration = request.values.get('DialCallDuration')
    recordingUrl = request.values.get('RecordingUrl')
    
    #Ozgur - firebase push -- working
    result = firebase.put('/User/Anthonyminnella/callHistory', new_callHistoryID, data={'callType': callType, 'callDuration': callDuration, 'callSID': callSid, 'recordingURI': recordingUrl, 'callDateTime': callDateTime, 'number': number, 'name': name, 'language': language})
    print result
    {u'name': u'-Io26123nDHkfybDIGl7'}
    
    return str(recordingUrl)

@app.route('/pushConfHistory', methods=['GET', 'POST'])
def pushConfHistory():
    
    new_callHistoryID = 'OzgurVatansever5599'
    
    #conference info
    conferenceSid = request.values.get('ConferenceSid')
    conferenceCallSid = request.values.get('CallSid')
    
    #Ozgur - firebase push -- working
    result = firebase.put('/User/Anthonyminnella/callHistory', new_callHistoryID, data={'callType': callType, 'conferenceSid': conferenceSid, 'conferenceCallSid': conferenceCallSid, 'callDateTime': callDateTime, 'number': number, 'name': name, 'language': language})
    
    print result
    {u'name': u'-Io26123nDHkfybDIGl7'}
    
    return str(recordingUrl)


@app.route('/pushRecordedConfHistory', methods=['GET', 'POST'])
def pushRecordedConfHistory():
    
    new_callHistoryID = 'OzgurVatansever5599'
    
    #conference info
    conferenceSid = request.values.get('ConferenceSid')
    conferenceCallSid = request.values.get('CallSid')
    recordingUrl = request.values.get('RecordingUrl')
    recordingDuration = request.values.get('Duration')
    recordingTimestamp = request.values.get('timestamp')
    
    #Ozgur - firebase push -- working
    result = firebase.put('/User/Anthonyminnella/callHistory', new_callHistoryID, data={'conferenceSid': conferenceSid, 'conferenceCallSid': conferenceCallSid, 'recordingDuration': recordingDuration, 'recordingDateTime': recordingTimestamp,  'recordingURI': recordingUrl})

    print result
    {u'name': u'-Io26123nDHkfybDIGl7'}
    
    return str(recordingUrl)


@app.route('/', methods=['GET', 'POST'])
def welcome():
  resp = twilio.twiml.Response()
  resp.say("Welcome to Twilio")
  return str(resp)

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
