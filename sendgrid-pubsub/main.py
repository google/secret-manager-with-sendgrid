# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# sengrid_pubsub - A Pub/Sub Google Cloud Function for calling Sendgrid
#
# Function arguments
#
#    event (dict):
#        The dictionary with data specific to this type of event.
#        The `@type` field maps to
#        
#        `type.googleapis.com/google.pubsub.v1.PubsubMessage`.
#        
#        The `data` field maps to the PubsubMessage data in a base64-encoded string.
#        The `attributes` field maps to the PubsubMessage attributes if any is
#        present.
#        
#    context (google.cloud.functions.Context):
#        
#        Metadata of triggering eveng including `event_id` which maps to the
#        PubsubMessage messageId, `timestamp` which maps to the PubsubMessage
#        publishTime, `event_type` which maps to`google.pubsub.topic.publish`,
#        and `resource` which is a dictionary that describes the service API
#        endpoint pubsub.googleapis.com, the triggering topic's name, and
#        the triggering event type
#        `type.googleapis.com/google.pubsub.v1.PubsubMessage`.

def sendgrid_pubsub(event, context):
    import base64
    import json
    import logging
    import sendgrid
    from flask import abort, Response
    from http import HTTPStatus
    from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent

    from google.cloud import secretmanager
    
    if 'data' not in event:
        error_message = 'send_mail: no data passed to Flask framework event'
        logging.error(error_message)
        return abort(HTTPStatus.BAD_REQUEST.value, error_message)

    try:
        event_data_json = json.loads(base64.b64decode(event['data']).decode('utf-8'))
    except Exception as e:
        error_message = 'send_mail: data does not contain a valid JSON string'
        logging.error(error_message)
        return abort(HTTPStatus.BAD_REQUEST.value, error_message)

    # Fetch the GCP project ID from the request JSON with the key
    # name "project_id."  If it is not present, raise an exception since
    # we cannot proceed further without a project ID.

    if 'project_id' in event_data_json:
        project_id = event_data_json['project_id']
    else:
        error_message = 'send_mail: project_id not found in request json or arguments'
        logging.error(error_message)
        return abort(HTTPStatus.BAD_REQUEST.value, error_message)

    # Fetch the "from address" from the request JSON with the key
    # name "from_address."  If it is not present, raise an exception since
    # we cannot proceed further without a from_address.

    if 'from_address' in event_data_json:
        from_address = event_data_json['from_address']
    else:
        error_message = 'send_mail: from_address not found in request json or arguments'
        logging.error(error_message)
        return abort(HTTPStatus.BAD_REQUEST.value, error_message)

    # Fetch the "to address" from the request JSON with the key
    # name "to_address."  If it is not present, raise an exception since
    # we cannot proceed further without a to_address.

    if 'to_address' in event_data_json:
        to_address = event_data_json['to_address']
    else:
        error_message = 'send_mail: to_address not found in request json or arguments'
        logging.error(error_message)
        return abort(HTTPStatus.BAD_REQUEST.value, error_message)

    # Fetch the message subject from the request JSON with the key
    # name "subject."  If it is not present, assume the value of '' (a zero
    # length string).

    if 'subject' in event_data_json:
        subject = event_data_json['subject']
    else:
        subject = ''
        
    # Fetch the message body from the request JSON with the key
    # name "content."  If it is not present, assume the value of '' (a zero
    # length string).

    if 'plain_text_content' in event_data_json:
        plain_text_content = event_data_json['plain_text_content']
    else:
        plain_text_content = ''

    # Fetch the name (not the value) of the secret from the request JSON
    # with the key name "secret."  If it is not present, assume the
    # value of "SENDGRID_API_KEY."

    if 'secret' in event_data_json:
        secret = event_data_json['secret']
    else:
        secret = 'SENDGRID_API_KEY'
    
    # Fetch the version of the secret from the request JSON
    # with the key name "secret_version."  If it is not present,
    # assume the value of "latest."

    if 'secret_version' in event_data_json:
        secret_version = event_data_json['secret_version']
    else:
        secret_version = 'latest'

    # Create the full secret name and retrieve the secret.
    # Raise an exception if the retrieval fails.

    client = secretmanager.SecretManagerServiceClient()
    full_secret_name = client.secret_version_path(project_id, secret, secret_version)
    
    try:
        response = client.access_secret_version(name=full_secret_name)
    except Exception as e:
        error_message = 'send_mail: unable to retrieve secret ' + full_secret_name
        logging.error(error_message)
        return abort(HTTPStatus.BAD_REQUEST.value, error_message)

    # Decode the encrypted secret and get the Sendgrid API key.
    
    sendgrid_api_key = response.payload.data.decode('UTF-8')
    
    # Use the Sendgrid API to send the message.
    
    sg = sendgrid.SendGridAPIClient(api_key = sendgrid_api_key)
    from_address = From(from_address)
    to_address = To(to_address)
    subject = Subject(subject)
    plain_text_content = PlainTextContent(plain_text_content)
    sendgrid_mail = Mail(
        from_email=from_address,
        to_emails=to_address,
        subject=subject,
        plain_text_content=plain_text_content)
    response = sg.send(message=sendgrid_mail)
    
    # Use the Sendgrid return status for the the Cloud Function status code.
    
    status_code = Response(response=response.body, status=response.status_code)
    return status_code
