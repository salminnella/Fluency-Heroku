import os
from flask import Flask, request
from twilio.util import TwilioCapability
from twilio.rest import TwilioRestClient
import twilio.twiml

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
  recordConference = request.values.get('Record')
  caller_id = os.environ.get("CALLER_ID", CALLER_ID)
  digits = request.values.get('SendDigits')
  
  if recordConference:
      output = "<Response><Dial timeout=\"10\" record=\"true\">415-123-4567</Dial></Response>"
      return str(output)
  
  if digits:
      output = "<Response><Dial callerId=\"5204403178\"><Number sendDigits=\"wwwwww4860\">" + to + "</Number></Dial></Response>"
      return str(output)

  if conf_name:
      #resp = "<Response><Dial callerId=\"" + caller_id + "\"><Conference mute=\"false\" startConferenceOnEnter=\"true\" endConferenceOnExit=\"true\">" + conf_name + "</Conference></Dial></Response>"
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
    #resp.dial(callerId=caller_id).conference(conf_name)
    #resp = "<Response><Dial timeout=\"10\" record=\"true\"><Conference>anton</Conference>" + to + "</Dial></Response>"
    resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
  else:
    # client -> PSTN
    resp.dial(to, callerId=caller_id)
  return str(resp)

@app.route('/join', methods=['GET', 'POST'])
def join():
    conf_name = request.values.get('ConfName')
    to = request.values.get('To')
    client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)

    call = client.calls.create(url="https://fluency-1.herokuapp.com/call?ConfName=anthony",
                           to="+15054016380",
                           from_="+15204403178")
    print(call.sid)
    
    resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
    return str(resp)

@app.route('/', methods=['GET', 'POST'])
def welcome():
  resp = twilio.twiml.Response()
  resp.say("Welcome to Twilio")
  return str(resp)

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
