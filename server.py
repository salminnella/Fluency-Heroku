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
  global callType
  callType = request.values.get('callType')
  global name
  name = request.values.get('name')
  global number
  number = request.values.get('number')
  global callDateTime
  callDateTime = request.values.get('CallDateTime')
  global srcLanguage
  srcLanguage = request.values.get('sourceLanguage')
  global interLanguage
  interLanguage = request.values.get('interpreterLanguage')
  global countryCode
  countryCode = request.values.get('countryCode')
  global new_callHistoryID
  new_callHistoryID = request.values.get('nextCallHistoryId')
  global contactImage
  contactImage = request.values.get('contactImage')
  
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
    urlString = 'https://fluency-1.herokuapp.com/conference?ConfName=' + str(conf_name)
    call = twilioClient.calls.create(url=urlString,
                           to = request.values.get('To'),
                           from_="+15204403178"
                           )
    
    resp = "<Response><Dial><Conference>" + conf_name + "</Conference></Dial></Response>"
    return str(resp)

@app.route('/pushCallHistory', methods=['GET', 'POST'])
def pushCallHistory():
    
    #one call to interpreter - Face to face
    callSid = request.values.get('DialCallSid')
    callDuration = request.values.get('DialCallDuration')

    #Ozgur - firebase push -- working
    result = firebase.put('/User/Anthonyminnella/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': callDuration, 'callSID': callSid, 'callDateTime': callDateTime, 'number': number, 'name': name, 'srcLanguage': srcLanguage, 'interLanguage': interLanguage, 'countryCode': countryCode})

    {u'name': u'-Io26123nDHkfybDIGl7'}

    return '<Response></Response>'

@app.route('/pushRecordedCallHistory', methods=['GET', 'POST'])
def pushRecordedCallHistory():
    
    #one call to interpreter - recorded - Face to face
    callSid = request.values.get('DialCallSid')
    callDuration = request.values.get('DialCallDuration')
    recordingUrl = request.values.get('RecordingUrl')
    
    #Ozgur - firebase push -- working
    result = firebase.put('/User/Anthonyminnella/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': callDuration, 'callSID': callSid, 'callDateTime': callDateTime, 'number': number, 'name': name, 'recordingURI': recordingUrl, 'srcLanguage': srcLanguage, 'interLanguage': interLanguage, 'countryCode': countryCode})
    
    {u'name': u'-Io26123nDHkfybDIGl7'}
    
    return '<Response></Response>'

@app.route('/pushConfHistory', methods=['GET', 'POST'])
def pushConfHistory():
    
    #conference info
    conferenceSid = request.values.get('ConferenceSid')
    conferenceCallSid = request.values.get('CallSid')
    
    client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
    conference = client.conferences.get(conferenceSid)
    timestamp_created = mktime_tz(parsedate_tz(conference.date_created))
    timestamp_updated = mktime_tz(parsedate_tz(conference.date_updated))
    
    duration = str(timestamp_updated - timestamp_created)
    
    #Ozgur - firebase push -- working
    result = firebase.put('/User/Anthonyminnella/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': duration, 'conferenceSID': conferenceSid, 'callSID': conferenceCallSid, 'callDateTime': callDateTime, 'number': number, 'name': name, 'srcLanguage': srcLanguage, 'interLanguage': interLanguage, 'countryCode': countryCode, 'contactImage': contactImage})

    {u'name': u'-Io26123nDHkfybDIGl7'}
    
    return str(conferenceCallSid)


@app.route('/pushRecordedConfHistory', methods=['GET', 'POST'])
def pushRecordedConfHistory():
    
    #conference info - recorded
    conferenceSid = request.values.get('ConferenceSid')
    conferenceCallSid = request.values.get('CallSid')
    recordingUrl = request.values.get('RecordingUrl')
    duration = request.values.get('Duration')
    recordingTimestamp = request.values.get('timestamp')
    
    #Ozgur - firebase push -- working
    result = firebase.put('/User/Anthonyminnella/callHistory', new_callHistoryID, data={'callHistoryId': new_callHistoryID, 'callType': callType, 'callDuration': duration, 'conferenceSID': conferenceSid, 'callSID': conferenceCallSid,'callDateTime': callDateTime,  'recordingURI': recordingUrl, 'number': number, 'name': name, 'srcLanguage': srcLanguage, 'interLanguage': interLanguage, 'countryCode': countryCode, 'contactImage': contactImage})

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
    cents = int(cost)

    response = chargeCard(custID, cents)
    
    return response

@app.route('/charge', methods=['GET', 'POST'])
def chargeCreditCard():
    b_charge = ""
    stripeToken = request.values.get('stripeToken')
    cents = 300

#    response = chargeCard(stripeToken, cents)
#
#    return response
    try:
        # Use Stripe's library to make requests...
        b_charge = stripe.Charge.create(
                                        amount=cents,
                                        currency="usd",
                                        source=stripeToken,
                                        description="Charge for salminnella@gmail.com"
                                        )
        chargeResponse = b_charge.id
        pass
    except stripe.CardError as e:
        # Since it's a decline, stripe.error.CardError will be caught
        body = e.json_body
        err  = body['error']
#        chargeResponse = err['message']
        chargeResponse = err
        pass
    except stripe.InvalidRequestError as e:
        # Invalid parameters were supplied to Stripe's API
        body = e.json_body
        err  = body['error']
#        chargeResponse = err['message']
        chargeResponse = err
        pass
    except stripe.AuthenticationError as e:
        # Authentication with Stripe's API failed
        # (maybe you changed API keys recently)
        body = e.json_body
        err  = body['error']
#        chargeResponse = err['message']
        chargeResponse = err
        pass
    except stripe.APIConnectionError as e:
        # Network communication with Stripe failed
        body = e.json_body
        err  = body['error']
        chargeResponse = err['message']
        pass
    except stripe.StripeError as e:
        # Display a very generic error to the user, and maybe send
        # yourself an email
        body = e.json_body
        err  = body['error']
        chargeResponse = err['message']
        pass
    except stripe.RateLimitError as e:
        # Too many requests made to the API too quickly
        body = e.json_body
        err  = body['error']
        chargeResponse = err['message']
        pass
    except Exception as e:
        # Something else happened, completely unrelated to Stripe
        body = e.json_body
        err  = body['error']
        chargeResponse = err['message']
        pass

    return str(chargeResponse)



@app.route('/preauth', methods=['GET', 'POST'])
def authCreditCard():
    custID = request.values.get('customerID')
    
#    response = chargeCard(custID, 2500)

#    return response
#    return str("there was a problem with the preauth")
#    return str("{u\"type\": u\"card_error\", u\"code": u\"card_declined\", u\"message\": u\"Your card was declined.\", u\"charge\": u\"ch_18wIxPKx8RwYBt0sRVymHrb9\"}")

    try:
        # Use Stripe's library to make requests...
        a_charge = stripe.Charge.create(
                                        amount=2500,
                                        currency="usd",
                                        capture="false",
                                        customer=custID,
                                        description="Charge for salminnella@gmail.com"
                                        )
        preAuthResponse = a_charge.id
        
        pass
    except stripe.CardError as e:
        # Since it's a decline, stripe.error.CardError will be caught
        body = e.json_body
        err  = body['error']
        preAuthResponse = err['message']
    except stripe.error.RateLimitError as e:
        # Too many requests made to the API too quickly
        body = e.json_body
        err  = body['error']
        preAuthResponse = err['message']
        pass
    except stripe.error.InvalidRequestError as e:
        # Invalid parameters were supplied to Stripe's API
        body = e.json_body
        err  = body['error']
        preAuthResponse = err['message']
        pass
    except stripe.error.AuthenticationError as e:
        # Authentication with Stripe's API failed
        # (maybe you changed API keys recently)
        body = e.json_body
        err  = body['error']
        preAuthResponse = err['message']
        pass
    except stripe.error.APIConnectionError as e:
        # Network communication with Stripe failed
        body = e.json_body
        err  = body['error']
        preAuthResponse = err['message']
        pass
    except stripe.error.StripeError as e:
        # Display a very generic error to the user, and maybe send
        # yourself an email
        body = e.json_body
        err  = body['error']
        preAuthResponse = err['message']
        pass
    except Exception as e:
        # Something else happened, completely unrelated to Stripe
        body = e.json_body
        err  = body['error']
        preAuthResponse = err['message']
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


def chargeCard( str, chargeAmount ):
    try:
        # Use Stripe's library to make requests...
        b_charge = stripe.Charge.create(
                                        amount=chargeAmount,
                                        currency="usd",
                                        source=str,
                                        description="Charge for salminnella@gmail.com"
                                        )
        chargeResponse = b_charge.id
        pass
    except stripe.CardError as e:
        # Since it's a decline, stripe.error.CardError will be caught
        body = e.json_body
        err  = body['error']
        chargeResponse = err['message']
        pass
    except stripe.InvalidRequestError as e:
        # Invalid parameters were supplied to Stripe's API
        body = e.json_body
        err  = body['error']
        #        chargeResponse = err['message']
        chargeResponse = err
        pass
    except stripe.AuthenticationError as e:
        # Authentication with Stripe's API failed
        # (maybe you changed API keys recently)
        body = e.json_body
        err  = body['error']
        #        chargeResponse = err['message']
        chargeResponse = err
        pass
    except stripe.APIConnectionError as e:
        # Network communication with Stripe failed
        body = e.json_body
        err  = body['error']
        chargeResponse = err['message']
        pass
    except stripe.StripeError as e:
        # Display a very generic error to the user, and maybe send
        # yourself an email
        body = e.json_body
        err  = body['error']
        chargeResponse = err['message']
        pass
    except stripe.RateLimitError as e:
        # Too many requests made to the API too quickly
        body = e.json_body
        err  = body['error']
        chargeResponse = err['message']
        pass
    except Exception as e:
        # Something else happened, completely unrelated to Stripe
        body = e.json_body
        err  = body['error']
        chargeResponse = err['message']
        pass

    return str(chargeResponse)

@app.route('/', methods=['GET', 'POST'])
def welcome():
  resp = twilio.twiml.Response()
  resp.say("Welcome to Twilio")
  return str(resp)

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
