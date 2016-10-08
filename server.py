import os
import stripe
from stripe import (  # noqa
                          StripeError, APIError, APIConnectionError, AuthenticationError, CardError,
                          InvalidRequestError)
from flask import Flask, request
from twilio.util import TwilioCapability
from twilio.rest import TwilioRestClient
import twilio.twiml
from firebase import firebase
from email.utils import parsedate_tz, mktime_tz
import json
import urllib
from urllib import urlencode

# Account Sid and Auth Token can be found in your account dashboard
ACCOUNT_SID = 'ACdd8953205cab360450e486f1a3a52fe9'
AUTH_TOKEN = '4eea9c2481e3f5f8b630a7d30942a1b6'

global firebase
firebase = firebase.FirebaseApplication('https://project-5176964787746948725.firebaseio.com')

# TwiML app outgoing connections will use
APP_SID = 'AP2e55b89356bc0bb298806f1289e827cc'
stripe.api_key = "sk_test_ztkUGrXPoHOOarxOH9QviyJk"

CALLER_ID = '+1 855-999-9083'
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
  callType = request.values.get('callType')
  name = request.values.get('name')
  number = request.values.get('number')
  callDateTime = request.values.get('CallDateTime')
  srcLanguage = request.values.get('sourceLanguage')
  interLanguage = request.values.get('interpreterLanguage')
  countryCode = request.values.get('countryCode')
  new_callHistoryID = request.values.get('nextCallHistoryId')
  userId = request.values.get('userID')

  params = "userID=" + userId + "%26nextCallHistoryId=" + new_callHistoryID + "%26countryCode=" + urllib.quote_plus(countryCode) + "%26interpreterLanguage=" + urllib.quote(interLanguage) + "%26sourceLanguage=" + urllib.quote(srcLanguage) + "%26CallDateTime=" + urllib.quote_plus(callDateTime) + "%26number=" + number + "%26name=" + name + "%26callType=" + urllib.quote(callType)
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
        resp = "<Response><Dial><Conference record=\"record-from-start\" eventCallbackUrl=\"https://fluency-1.herokuapp.com/pushRecordedConfHistory?" + params + "\" endConferenceOnExit=\"true\">" + to[11:] + "</Conference></Dial></Response>"
    else:
        resp = "<Response><Dial><Conference statusCallback=\"https://fluency-1.herokuapp.com/pushConfHistory?" + params + "\" statusCallbackEvent=\"end\" endConferenceOnExit=\"true\">" + to[11:] + "</Conference></Dial></Response>"
  else:
    # client -> PSTN
    if recordCall:
        resp = "<Response><Dial record=\"true\" callerId=\"" + caller_id + "\" action=\"https://fluency-1.herokuapp.com/pushRecordedCallHistory?" + params + "\" method=\"POST\">" + to + "</Dial></Response>"
    else:
        #resp.dial(to, callerId=caller_id)
        resp = "<Response><Dial callerId=\"" + caller_id + "\" action=\"https://fluency-1.herokuapp.com/pushCallHistory?" + params + "\" method=\"POST\">" + to + "</Dial></Response>"

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
    urlString = 'https://fluency-1.herokuapp.com/conference?ConfName=' + str(conf_name)
    call = twilioClient.calls.create(url=urlString,
                           to = request.values.get('To'),
                           from_="+15204403178"
                           )

    resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
    return str(resp)

@app.route('/pushCallHistory', methods=['GET', 'POST'])
def pushCallHistory():
    params = request.query_string
    d = dict(item.split("=") for item in params.split("%26"))

    #one call to interpreter - Face to face
    callSid = request.values.get('DialCallSid')
    callDuration = request.values.get('DialCallDuration')

    userID = d['userID']
    callTypeEncoded = d['callType']
    callType = callTypeEncoded.replace("%20", " ")
    name = d['name']
    number = d['number']
    callDateTimeEncoded = d['CallDateTime']
    callDateTime = callDateTimeEncoded.replace("%2F", "/")
    srcLanguageEncoded = d['sourceLanguage']
    srcLanguage = srcLanguageEncoded.replace("%20", " ")
    interLanguageEncoded = d['interpreterLanguage']
    interLanguage = interLanguageEncoded.replace("%20", " ")
    countryCodeEncoded = d['countryCode']
    countryCode = countryCodeEncoded.replace("%2B", "+")
    new_callHistoryID = d['nextCallHistoryId']

    #Ozgur - firebase push -- working
    result = firebase.put('/User/' + str(userID) + '/callHistory', str(new_callHistoryID), data={'callHistoryId': str(new_callHistoryID), 'callType': str(callType), 'callDuration': str(callDuration), 'callSID': str(callSid), 'callDateTime': str(callDateTime), 'number': str(number), 'name': str(name), 'srcLanguage': str(srcLanguage), 'interLanguage': str(interLanguage), 'countryCode': str(countryCode)})

    {u'name': u'-Io26123nDHkfybDIGl7'}

    return '<Response></Response>'

@app.route('/pushRecordedCallHistory', methods=['GET', 'POST'])
def pushRecordedCallHistory():
    params = request.query_string
    d = dict(item.split("=") for item in params.split("%26"))
    #one call to interpreter - recorded - Face to face
    callSid = request.values.get('DialCallSid')
    callDuration = request.values.get('DialCallDuration')
    recordingUrl = request.values.get('RecordingUrl')
    recordingID = recordingUrl[89:]

    userID = d['userID']
    callTypeEncoded = d['callType']
    callType = callTypeEncoded.replace("%20", " ")
    name = d['name']
    number = d['number']
    callDateTimeEncoded = d['CallDateTime']
    callDateTime = callDateTimeEncoded.replace("%2F", "/")
    srcLanguageEncoded = d['sourceLanguage']
    srcLanguage = srcLanguageEncoded.replace("%20", " ")
    interLanguageEncoded = d['interpreterLanguage']
    interLanguage = interLanguageEncoded.replace("%20", " ")
    countryCodeEncoded = d['countryCode']
    countryCode = countryCodeEncoded.replace("%2B", "+")
    new_callHistoryID = d['nextCallHistoryId']

    #Ozgur - firebase push -- working
    result = firebase.put('/User/' + userID + '/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': callDuration, 'callSID': callSid, 'callDateTime': callDateTime, 'number': number, 'name': name, 'recordingURI': recordingUrl, 'srcLanguage': srcLanguage, 'interLanguage': interLanguage, 'countryCode': countryCode, 'recordingID': recordingID})

    {u'name': u'-Io26123nDHkfybDIGl7'}

    return '<Response></Response>'

@app.route('/pushConfHistory', methods=['GET', 'POST'])
def pushConfHistory():
    params = request.query_string
    pm = params.replace("%3D", "=")
    d = dict(item.split("=") for item in pm.split("%26"))
    #conference info
    conferenceSid = request.values.get('ConferenceSid')
    conferenceCallSid = request.values.get('CallSid')
    client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
    conference = client.conferences.get(conferenceSid)
    timestamp_created = mktime_tz(parsedate_tz(conference.date_created))
    timestamp_updated = mktime_tz(parsedate_tz(conference.date_updated))
    duration = str(timestamp_updated - timestamp_created)

    userID = d['userID']
    callTypeEncoded = d['callType']
    callType = callTypeEncoded.replace("%20", " ")
    name = d['name']
    number = d['number']
    callDateTimeEncoded = d['CallDateTime']
    callDateTime = callDateTimeEncoded.replace("%2F", "/")
    srcLanguageEncoded = d['sourceLanguage']
    srcLanguage = srcLanguageEncoded.replace("%20", " ")
    interLanguageEncoded = d['interpreterLanguage']
    interLanguage = interLanguageEncoded.replace("%20", " ")
    countryCodeEncoded = d['countryCode']
    countryCode = countryCodeEncoded.replace("%2B", "+")
    new_callHistoryID = d['nextCallHistoryId']

    #Ozgur - firebase push -- working
    result = firebase.put('/User/' + userID + '/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': duration, 'conferenceSID': conferenceSid, 'callSID': conferenceCallSid, 'callDateTime': callDateTime, 'number': number, 'name': name, 'srcLanguage': srcLanguage, 'interLanguage': interLanguage, 'countryCode': countryCode})

    {u'name': u'-Io26123nDHkfybDIGl7'}

    return str(conferenceCallSid)


@app.route('/pushRecordedConfHistory', methods=['GET', 'POST'])
def pushRecordedConfHistory():
    #conference info - recorded
    conferenceSid = request.values.get('ConferenceSid')
    conferenceCallSid = request.values.get('CallSid')
    recordingUrl = request.values.get('RecordingUrl')
    recordingID = recordingUrl[89:]
    duration = request.values.get('Duration')
    recordingTimestamp = request.values.get('timestamp')

    userID = request.values.get('userID')
    callType = request.values.get('callType')
    name = request.values.get('name')
    number = request.values.get('number')
    callDateTime = request.values.get('CallDateTime')
    srcLanguage = request.values.get('sourceLanguage')
    interLanguage = request.values.get('interpreterLanguage')
    countryCode = request.values.get('countryCode')
    new_callHistoryID = request.values.get('nextCallHistoryId')

    #Ozgur - firebase push -- working
    result = firebase.put('/User/' + userID + '/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': duration, 'conferenceSID': conferenceSid, 'callSID': conferenceCallSid,'callDateTime': callDateTime,  'recordingURI': recordingUrl, 'number': number, 'name': name, 'srcLanguage': srcLanguage, 'interLanguage': interLanguage, 'countryCode': countryCode, 'recordingID': recordingID})

    {u'name': u'-Io26123nDHkfybDIGl7'}

    return str(new_callHistoryID)

@app.route('/delete-recording', methods=['GET', 'POST'])
def recording():
    recordingSID = request.values.get('RecordingSID')
    client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
    client.recordings.delete(recordingSID)

    return str(recordingSID)

@app.route('/create_customer', methods=['GET', 'POST'])
def create_customer():

    #token = request.POST['stripeToken']
    stripeToken = request.values.get('stripeToken')
    custDescription = request.values.get('description')

    # Create a Customer
    customer = stripe.Customer.create(
                                      source = stripeToken,
                                      description = custDescription
                                      )

    return str(customer.id)

@app.route('/retrieve_customer')
def retrieve_customer():

    custID = request.values.get('customerID')
    stripeCustomer = stripe.Customer.retrieve(custID)

    return str(stripeCustomer)

@app.route('/charge_customer', methods=['GET', 'POST'])
def chargeCustomer():
    custID = request.values.get('customerID')
    cost = request.values.get('totalCost')
    emailAddress = request.values.get('emailAddress')
    cents = int(cost)

    response = chargeCard(custID, cents, emailAddress)

    return response

@app.route('/preauth', methods=['GET', 'POST'])
def authCreditCard():
    custID = request.values.get('customerID')
    emailAddress = request.values.get('emailAddress')

    try:
        # Use Stripe's library to make requests...
        a_charge = stripe.Charge.create(
                                        amount=2500,
                                        currency="usd",
                                        capture="false",
                                        customer=custID,
                                        description="PreAuth for " + emailAddress
                                        )
        preAuthResponse = "{ \"charge\": \"" + a_charge.id + "\"}"
        pass
    except stripe.CardError as e:
        # Since it's a decline, stripe.error.CardError will be caught
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        preAuthResponse = jsonArray
#        preAuthResponse = err['message']
    except stripe.error.RateLimitError as e:
        # Too many requests made to the API too quickly
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        preAuthResponse = jsonArray
        pass
    except stripe.error.InvalidRequestError as e:
        # Invalid parameters were supplied to Stripe's API
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        preAuthResponse = jsonArray
        pass
    except stripe.error.AuthenticationError as e:
        # Authentication with Stripe's API failed
        # (maybe you changed API keys recently)
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        preAuthResponse = jsonArray
        pass
    except stripe.error.APIConnectionError as e:
        # Network communication with Stripe failed
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        preAuthResponse = jsonArray
        pass
    except stripe.error.StripeError as e:
        # Display a very generic error to the user, and maybe send
        # yourself an email
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        preAuthResponse = jsonArray
        pass
    except Exception as e:
        # Something else happened, completely unrelated to Stripe
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        preAuthResponse = jsonArray
        pass

    return str(preAuthResponse)



@app.route('/cancel_preauth', methods=['GET', 'POST'])
def cancel_preauth():
    chargeID = request.values.get('chargeID')
    ch = stripe.Charge.retrieve(chargeID)
    re = ch.refund()

    return str(chargeID)

@app.route('/update_customer', methods=['GET', 'POST'])
def update_customer():

    stripeToken = request.values.get('stripeToken')
    custID = request.values.get('customerID')

    cu = stripe.Customer.retrieve(custID)
    cu.source = stripeToken
    cu.save()

    return str('updated customer card')


def chargeCard( customerID, chargeAmount, emailAddress ):
    try:
        # Use Stripe's library to make requests...
        b_charge = stripe.Charge.create(
                                        amount=chargeAmount,
                                        currency="usd",
                                        customer=customerID,
                                        receipt_email=emailAddress
                                        description="Charge for " + emailAddress
                                        )
        chargeResponse = "{ \"charge\": \"" + b_charge.id + "\"}"

        pass
    except stripe.CardError as e:
        # Since it's a decline, stripe.error.CardError will be caught
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        chargeResponse = jsonArray
        pass
    except stripe.InvalidRequestError as e:
        # Invalid parameters were supplied to Stripe's API
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        chargeResponse = jsonArray
        pass
    except stripe.AuthenticationError as e:
        # Authentication with Stripe's API failed
        # (maybe you changed API keys recently)
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        chargeResponse = jsonArray
        pass
    except stripe.APIConnectionError as e:
        # Network communication with Stripe failed
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        chargeResponse = jsonArray
        pass
    except stripe.StripeError as e:
        # Display a very generic error to the user, and maybe send
        # yourself an email
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        chargeResponse = jsonArray
        pass
    except stripe.RateLimitError as e:
        # Too many requests made to the API too quickly
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        chargeResponse = jsonArray
        pass
    except Exception as e:
        # Something else happened, completely unrelated to Stripe
        body = e.json_body
        err  = body['error']
        jsonArray = json.dumps(err)
        chargeResponse = jsonArray
        pass

    return chargeResponse

@app.route('/', methods=['GET', 'POST'])
def welcome():
  resp = twilio.twiml.Response()
  resp.say("Welcome to Twilio")
  return str(resp)

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
