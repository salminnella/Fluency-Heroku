import os
import stripe
from stripe import (  # noqa
                          StripeError, APIError, APIConnectionError, AuthenticationError, CardError,
                          InvalidRequestError)
from flask import Flask, request, url_for
from twilio.util import TwilioCapability
from twilio.rest import TwilioRestClient
import twilio.twiml
from firebase import firebase
from email.utils import parsedate_tz, mktime_tz
import json
import urllib
from urllib import urlencode

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
APP_SID = os.environ.get("APP_SID")
API_KEY = os.environ.get("API_KEY")
API_KEY_SECRET = os.environ.get("API_SECRET")
PUSH_CREDENTIAL_SID = os.environ.get("PUSH_CREDENTIAL_SID")
stripe.api_key = os.environ.get("STRIPE_API_KEY")
# Firebase url
global firebase
firebase = firebase.FirebaseApplication('https://project-5176964787746948725.firebaseio.com')

CLIENT = 'Fluency'
CALLER_ID = os.environ.get("CALLER_ID")
app = Flask(__name__)

@app.route('/token')
def token():
  capability = TwilioCapability(ACCOUNT_SID, AUTH_TOKEN)
  # This allows outgoing connections to TwiML application
  if request.values.get('allowOutgoing') != 'false':
     capability.allow_client_outgoing(APP_SID)
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
  srcLanguageIso = request.values.get('sourceLanguageIso')
  interLanguage = request.values.get('interpreterLanguage')
  interLanguageIso = request.values.get('interpreterLanguageIso')
  countryCode = request.values.get('countryCode')
  new_callHistoryID = request.values.get('nextCallHistoryId')
  userId = request.values.get('userID')

  params = "userID=" + userId + "%26nextCallHistoryId=" + new_callHistoryID + "%26countryCode=" + urllib.quote_plus(countryCode) + "%26interpreterLanguage=" + urllib.quote(interLanguage) + "%26interpreterLanguageIso=" + urllib.quote(interLanguageIso) + "%26sourceLanguage=" + urllib.quote(srcLanguage) + "%26sourceLanguageIso=" + urllib.quote(srcLanguageIso) + "%26CallDateTime=" + urllib.quote_plus(callDateTime) + "%26number=" + number + "%26name=" + name + "%26callType=" + urllib.quote(callType)
  # params = "userID=" + userId + "&nextCallHistoryId=" + new_callHistoryID + "&countryCode=" + urllib.quote_plus(countryCode) + "&interpreterLanguage=" + urllib.quote(interLanguage) + "&interpreterLanguageIso=" + urllib.quote(interLanguageIso) + "&sourceLanguage=" + urllib.quote(srcLanguage) + "&sourceLanguageIso=" + urllib.quote(srcLanguageIso) + "&CallDateTime=" + urllib.quote_plus(callDateTime) + "&number=" + number + "&name=" + name + "&callType=" + urllib.quote(callType)

  resp = twilio.twiml.Response()
  from_value = request.values.get('From')
  conf_name = request.values.get('ConfName')
  to = request.values.get('To')
  recordConference = request.values.get('RecordConf')
  recordCall = request.values.get('RecordCall')
  # caller_id = os.environ.get("CALLER_ID")
  caller_id = CALLER_ID
  digits = request.values.get('SendDigits')
  print 'interpreter digits = ', str(digits)

  if conf_name:
      resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
      return resp

  if not (from_value and to):
    resp.say("Invalid request")
    return str(resp)

  from_client = from_value.startswith('client')
  caller_id = CALLER_ID

  if not from_client:
    # PSTN -> client
    resp.dial(callerId=from_value).client(CLIENT)
  elif to.startswith("client:"):
    # client -> client
    resp.dial(callerId=from_value).client(to[7:])
  elif to.startswith("conference:"):
    # client -> conference
    if recordConference:
        resp = "<Response><Dial><Conference record=\"record-from-start\" recordingStatusCallback=\"https://fluency-1.herokuapp.com/pushRecordedConfHistory?" + params + "\" statusCallbackEvent=\"join leave end\" endConferenceOnExit=\"true\">" + to[11:] + "</Conference></Dial></Response>"
        # resp = "<Response><Dial><Conference record=\"record-from-start\" eventCallbackUrl=\"https://fluency-1.herokuapp.com/pushRecordedConfHistory?" + params + "\" endConferenceOnExit=\"true\"><Number sendDigits=\"" + digits + "\">" + to[11:] + "</Number></Conference></Dial></Response>"
    else:
        # resp = "<Response><Dial><Conference statusCallback=\"https://fluency-1.herokuapp.com/pushConfHistory?" + params + "\" statusCallbackEvent=\"end\" endConferenceOnExit=\"true\"><Number sendDigits=\"" + digits + "\">" + to[11:] + "</Number></Conference></Dial></Response>"
        resp = "<Response><Dial><Conference statusCallback=\"https://fluency-1.herokuapp.com/pushConfHistory?" + params + "\" statusCallbackEvent=\"join leave end\" endConferenceOnExit=\"true\">" + to[11:] + "</Conference></Dial></Response>"
  else:
    # client -> PSTN
    if recordCall:
        resp = "<Response><Dial record=\"record-from-answer\" callerId=\"" + caller_id + "\" method=\"POST\"><Number url=\"https://fluency-1.herokuapp.com/sayRecorded\" statusCallbackEvent=\"answered completed\" statusCallback=\"https://fluency-1.herokuapp.com/pushRecordedCallHistory?" + params + "\" sendDigits=\"" + digits + "\">" + to + "</Number></Dial></Response>"
    else:
        resp = "<Response><Dial callerId=\"" + caller_id + "\" method=\"POST\"><Number statusCallbackEvent=\"answered completed\" statusCallback=\"https://fluency-1.herokuapp.com/pushCallHistory?" + params + "\" sendDigits=\"" + digits + "\">" + to + "</Number></Dial></Response>"

  return str(resp)

@app.route('/conference', methods=['GET', 'POST'])
def conference():
    # instructions to twilio when call is answered
    # firebase push when call is answered to trigger appropriate timer start
    print '/conference was called'
    conf_name = request.values.get('ConfName')
    thirdParty = request.values.get('thirdParty')
    print '/conference: thirdParty = ', str(thirdParty)
    if thirdParty == 'interpreter':
        result = firebase.patch('/User/' + conf_name + '/callStatus', {'answered': thirdParty})
        {u'name': u'-Io26123nDHkfybDIGl7'}
    elif thirdParty == 'callee':
        result = firebase.patch('/User/' + conf_name + '/callStatus', {'answered': thirdParty})
        {u'name': u'-Io26123nDHkfybDIGl7'}

    resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
    return resp


@app.route('/join', methods=['GET', 'POST'])
def join():
    # called from android to join either the interpreter or callee to the conference
    conf_name = request.values.get('ConfName')
    to = request.values.get('To')
    thirdParty = request.values.get('thirdParty')
    digits = request.values.get('SendDigits')
    print '/join: thirdParty = ', thirdParty
    print '/join: digits = ', digits
    twilioClient = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
    call = twilioClient.calls.create(url=url_for('.conference',
                                                 ConfName=conf_name,
                                                 thirdParty=thirdParty,
                                                 _external=True),
                                     to = to,
                                     send_digits=digits,
                                     from_=CALLER_ID)

    # resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
    resp = "<Response></Response>"
    return str(resp)

@app.route('/sayRecorded', methods=['GET', 'POST'])
def sayRecorded():
    resp = "<Response><Say voice=\"alice\">This call will be recorded</Say></Response>"
    return str(resp)

@app.route('/pushCallHistory', methods=['GET', 'POST'])
def pushCallHistory():
    encodedParams = request.query_string
    params = encodedParams.replace("%3D", "=")
    # print 'Params = ', str(params)
    d = dict(item.split("=") for item in params.split("%26"))

    #one call to interpreter - Face to face
    callSid = request.values.get('CallSid')
    callDuration = request.values.get('CallDuration')
    callStatus = request.values.get('CallStatus')
    userID = d['userID']
    callTypeEncoded = d['callType']
    callType = callTypeEncoded.replace("%20", " ")
    name = d['name']
    number = d['number']
    callDateTimeEncoded = d['CallDateTime']
    callDateTime = callDateTimeEncoded.replace("%2F", "/")
    srcLanguageEncoded = d['sourceLanguage']
    srcLanguageIsoEncoded = d['sourceLanguageIso']
    srcLanguage = srcLanguageEncoded.replace("%20", " ")
    srcLanguageIso = srcLanguageIsoEncoded.replace("%20", " ")
    interLanguageEncoded = d['interpreterLanguage']
    interLanguageIsoEncoded = d['interpreterLanguageIso']
    interLanguage = interLanguageEncoded.replace("%20", " ")
    interLanguageIso = interLanguageIsoEncoded.replace("%20", " ")
    countryCodeEncoded = d['countryCode']
    countryCode = countryCodeEncoded.replace("%2B", "+")
    new_callHistoryID = d['nextCallHistoryId']

    print 'Call Status = ', callStatus

    if callStatus == 'in-progress':
        result = firebase.patch('/User/' + userID + '/callStatus', {'answered': 'true'})
        {u'name': u'-Io26123nDHkfybDIGl7'}
    elif callStatus == 'completed':
        #Ozgur - firebase push -- working
        result = firebase.put('/User/' + str(userID) + '/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': callDuration, 'callSID': callSid, 'callDateTime': callDateTime, 'number': number, 'name': name, 'srcLanguage': srcLanguage, 'srcLanguageIso': srcLanguageIso, 'interLanguage': interLanguage, 'interLanguageIso': interLanguageIso, 'countryCode': countryCode})
        {u'name': u'-Io26123nDHkfybDIGl7'}

    return '<Response></Response>'

@app.route('/pushRecordedCallHistory', methods=['GET', 'POST'])
def pushRecordedCallHistory():
    encodedParams = request.query_string
    params = encodedParams.replace("%3D", "=")
    # print 'Params = ', str(params)
    d = dict(item.split("=") for item in params.split("%26"))

    #one call to interpreter - recorded - Face to face
    callSid = request.values.get('CallSid')
    callDuration = request.values.get('CallDuration')
    recordingUrl = request.values.get('RecordingUrl')
    callStatus = request.values.get('CallStatus')
    recordingID = request.values.get('RecordingSid')
    userID = d['userID']
    callTypeEncoded = d['callType']
    callType = callTypeEncoded.replace("%20", " ")
    name = d['name']
    number = d['number']
    callDateTimeEncoded = d['CallDateTime']
    callDateTime = callDateTimeEncoded.replace("%2F", "/")
    srcLanguageEncoded = d['sourceLanguage']
    srcLanguageIsoEncoded = d['sourceLanguageIso']
    srcLanguage = srcLanguageEncoded.replace("%20", " ")
    srcLanguageIso = srcLanguageIsoEncoded.replace("%20", " ")
    interLanguageEncoded = d['interpreterLanguage']
    interLanguageIsoEncoded = d['interpreterLanguageIso']
    interLanguage = interLanguageEncoded.replace("%20", " ")
    interLanguageIso = interLanguageIsoEncoded.replace("%20", " ")
    countryCodeEncoded = d['countryCode']
    countryCode = countryCodeEncoded.replace("%2B", "+")
    new_callHistoryID = d['nextCallHistoryId']

    if callStatus == 'in-progress':
        result = firebase.patch('/User/' + userID + '/callStatus', {'answered': 'true'})
        {u'name': u'-Io26123nDHkfybDIGl7'}
    elif callStatus == 'completed':
        #Ozgur - firebase push -- working
        result = firebase.put('/User/' + userID + '/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': callDuration, 'callSID': callSid, 'callDateTime': callDateTime, 'number': number, 'name': name, 'recordingURI': recordingUrl, 'srcLanguage': srcLanguage, 'srcLanguageIso': srcLanguageIso, 'interLanguage': interLanguage, 'interLanguageIso': interLanguageIso, 'countryCode': countryCode, 'recordingID': recordingID})
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
    callStatus = request.values.get('StatusCallbackEvent')
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
    srcLanguageIsoEncoded = d['sourceLanguageIso']
    srcLanguage = srcLanguageEncoded.replace("%20", " ")
    srcLanguageIso = srcLanguageIsoEncoded.replace("%20", " ")
    interLanguageEncoded = d['interpreterLanguage']
    interLanguageIsoEncoded = d['interpreterLanguageIso']
    interLanguage = interLanguageEncoded.replace("%20", " ")
    interLanguageIso = interLanguageIsoEncoded.replace("%20", " ")
    countryCodeEncoded = d['countryCode']
    countryCode = countryCodeEncoded.replace("%2B", "+")
    new_callHistoryID = d['nextCallHistoryId']

    print 'call status = ', callStatus
    print 'conference sid = ', conferenceSid
    print 'conference call sid = ', conferenceCallSid

    if callStatus == 'participant-leave':
        #Ozgur - firebase push when conference member has left before the session ended
        result = firebase.patch('/User/' + userID + '/callLeft', {'sid': conferenceCallSid})
        {u'name': u'-Io26123nDHkfybDIGl7'}
    elif callStatus == 'participant-join':
        #firebase push when a participant joins
        result = firebase.patch('/User/' + userID + '/callJoin', {'sid': conferenceCallSid})
        {u'name': u'-Io26123nDHkfybDIGl7'}
    elif callStatus == 'conference-end':
        #Ozgur - firebase push when call is completed -- working
        print 'conference end was called'
        result = firebase.put('/User/' + userID + '/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': duration, 'conferenceSID': conferenceSid, 'callSID': conferenceCallSid, 'callDateTime': callDateTime, 'number': number, 'name': name, 'srcLanguage': srcLanguage, 'srcLanguageIso': srcLanguageIso, 'interLanguage': interLanguage, 'interLanguageIso': interLanguageIso, 'countryCode': countryCode})
        result = firebase.patch('/User/' + userID + '/callLeft', {'sid': 'none'} )
        result = firebase.patch('/User/' + userID + '/callJoin', {'sid': 'none'} )
        result = firebase.put('/User/' + userID + '/callStatus', {'answered': 'none'} )
        {u'name': u'-Io26123nDHkfybDIGl7'}


    return str(conferenceCallSid)


@app.route('/pushRecordedConfHistory', methods=['GET', 'POST'])
def pushRecordedConfHistory():
    #conference info - recorded
    conferenceSid = request.values.get('ConferenceSid')
    conferenceCallSid = request.values.get('CallSid')
    callStatus = request.values.get('StatusCallbackEvent')
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
    srcLanguageIso = request.values.get('sourceLanguageIso')
    interLanguage = request.values.get('interpreterLanguage')
    interLanguageIso = request.values.get('interpreterLanguageIso')
    countryCode = request.values.get('countryCode')
    new_callHistoryID = request.values.get('nextCallHistoryId')

    print 'call status = ', callStatus
    print 'conference sid = ', conferenceSid
    print 'conference call sid = ', conferenceCallSid

    if callStatus == 'participant-leave':
        #Ozgur - firebase push when conference member has left before the session ended
        result = firebase.patch('/User/' + userID + '/callLeft', {'sid': conferenceCallSid})
        {u'name': u'-Io26123nDHkfybDIGl7'}
    elif callStatus == 'participant-join':
        #firebase push when a participant joins
        result = firebase.patch('/User/' + userID + '/callJoin', {'sid': conferenceCallSid})
        {u'name': u'-Io26123nDHkfybDIGl7'}
    elif callStatus == 'conference-end':
        #Ozgur - firebase push when call is completed -- working
        print 'conference end was called'
        result = firebase.put('/User/' + userID + '/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': duration, 'conferenceSID': conferenceSid, 'callSID': conferenceCallSid,'callDateTime': callDateTime,  'recordingURI': recordingUrl, 'number': number, 'name': name, 'srcLanguage': srcLanguage, 'srcLanguageIso': srcLanguageIso, 'interLanguage': interLanguage, 'interLanguageIso': interLanguageIso, 'countryCode': countryCode, 'recordingID': recordingID})
        result = firebase.patch('/User/' + userID + '/callLeft', {'sid': 'none'} )
        result = firebase.patch('/User/' + userID + '/callJoin', {'sid': 'none'} )
        result = firebase.put('/User/' + userID + '/callStatus', {'answered': 'none'} )
        {u'name': u'-Io26123nDHkfybDIGl7'}


    return '<Response></Response>'

    #Ozgur - firebase push -- working
    # result = firebase.put('/User/' + userID + '/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': duration, 'conferenceSID': conferenceSid, 'callSID': conferenceCallSid,'callDateTime': callDateTime,  'recordingURI': recordingUrl, 'number': number, 'name': name, 'srcLanguage': srcLanguage, 'srcLanguageIso': srcLanguageIso, 'interLanguage': interLanguage, 'interLanguageIso': interLanguageIso, 'countryCode': countryCode, 'recordingID': recordingID})
    #
    # {u'name': u'-Io26123nDHkfybDIGl7'}
    #
    # return str(new_callHistoryID)

@app.route('/delete-recording', methods=['GET', 'POST'])
def recording():
    recordingSID = request.values.get('RecordingSID')
    client = TwilioRestClient(os.environ.get("ACCOUNT_SID"), os.environ.get("AUTH_TOKEN"))
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
                                        receipt_email=emailAddress,
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

# @app.route('/sayDisconnected', methods=['GET', 'POST'])
# def sayDisconnected():
#     resp = twilio.twiml.Response()
#     # resp.say("Caller Disconnected")
#
#     resp = "<Response><Say>Hello World disconnected</Say></Response>"
#
#     return str(resp)

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
