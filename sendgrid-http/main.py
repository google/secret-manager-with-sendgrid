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

# sendgrid_http - An HTTP Google Cloud Function for calling Sendgrid
#
# Please see the README.md file in the parent directory for information
# about deploying the function.
#
# Responds to any HTTP request.
#
# Args:
#   request (flask.Request): HTTP request object.
# 
# Returns:
#   The response text or any set of values that can be turned into a respons object using
#  `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    
def sendgrid_http(request):
    import logging
    import os
    import sendgrid
    from flask import abort, Response
    from http import HTTPStatus
    from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent

    from google.cloud import secretmanager

    request_json = request.get_json(silent=True)
    request_args = request.args

    # The Flask framework is used for Python Cloud Functions.
    # If there is no JSON string and no args, something is wrong.
    
    if not (request_json or request_args):
        error_message = 'send_mail: no arguments or request passed to Flask framework'
        logging.error(error_message)
        return abort(HTTPStatus.BAD_REQUEST.value, error_message)
        
    # Fetch the GCP project ID from the request JSON or args with the key
    # name "project_id."  If it is not present, raise an exception since
    # we cannot proceed further without a project ID.

    if request_json and 'project_id' in request_json:
        project_id = request_json['project_id']
    elif request_args and 'project_id' in request_args:
        project_id = request_args['project_id']
    else:
        error_message = 'send_mail: project_id not found in request json or arguments'
        logging.error(error_message)
        return abort(HTTPStatus.BAD_REQUEST.value, error_message)

    # Fetch the "from address" from the request JSON or args with the key
    # name "from_address."  If it is not present, raise an exception since
    # we cannot proceed further without a from_address.

    if request_json and 'from_address' in request_json:
        from_address = request_json['from_address']
    elif request_args and 'from_address' in request_args:
        from_address = request_args['from_address']
    else:
        error_message = 'send_mail: from_address not found in request json or arguments'
        logging.error(error_message)
        return abort(HTTPStatus.BAD_REQUEST.value, error_message)

    # Fetch the "to address" from the request JSON or args with the key
    # name "to_address."  If it is not present, raise an exception since
    # we cannot proceed further without a to_address.

    if request_json and 'to_address' in request_json:
        to_address = request_json['to_address']
    elif request_args and 'to_address' in request_args:
        to_address = request_args['to_address']
    else:
        error_message = 'send_mail: to_address not found in request json or arguments'
        logging.error(error_message)
        return abort(HTTPStatus.BAD_REQUEST.value, error_message)

    # Fetch the message subject from the request JSON or args with the key
    # name "subject."  If it is not present, assume the value of '' (a zero
    # length string).

    if request_json and 'subject' in request_json:
        subject = request_json['subject']
    elif request_args and 'subject' in request_args:
        subject = request_args['subject']
    else:
        subject = ''
        
    # Fetch the message body from the request JSON or args with the key
    # name "content."  If it is not present, assume the value of '' (a zero
    # length string).

    if request_json and 'plain_text_content' in request_json:
        plain_text_content = request_json['plain_text_content']
    elif request_args and 'plain_text_content' in request_args:
        plain_text_content = request_args['plain_text_content']
    else:
        plain_text_content = ''

    # Fetch the name (not the value) of the secret from the request JSON
    # or args with the key name "secret."  If it is not present, assume the
    # value of "SENDGRID_API_KEY."

    if request_json and 'secret' in request_json:
        secret = request_json['secret']
    elif request_args and 'secret' in request_args:
        secret = request_args['secret']
    else:
        secret = 'SENDGRID_API_KEY'
    
    # Fetch the version of the secret from the request JSON or args
    # with the key name "secret_version."  If it is not present,
    # assume the value of "latest."

    if request_json and 'secret_version' in request_json:
        secret_version = request_json['secret_version']
    elif request_args and 'secret_version' in request_args:
        secret_version = request_args['secret_version']
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
