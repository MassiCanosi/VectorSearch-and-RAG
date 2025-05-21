## Quart
import io
from quart import Quart, render_template, request, jsonify, redirect, url_for, session, send_file
from diskcache import Cache
import tempfile
import re
from datetime import datetime

## OpenAI
from openai import AzureOpenAI
import azure.cognitiveservices.speech as speechsdk
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.core.pipeline.transport import RequestsTransport

## Autenticazione
from authlib.jose import jwt, JsonWebKey
import os
from dotenv import load_dotenv
import aiohttp
import ast
import textwrap
import json


####### App Config + Env variables #######
app = Quart(__name__, static_folder='static', template_folder='templates')

# Load environment variables
load_dotenv()

# Session inizialization
app.config['SESSION_COOKIE_SECURE'] = True

# Cache inizialization
cache_dir = os.path.join(os.getcwd(), ".cache")
cache = Cache(directory=".cache")

TENANT_ID = os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
SPEECH_KEY = os.getenv('SPEECH_KEY')
JWKS_URL = f'https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys'


############ Authentication ############
deploy = os.getenv("DEPLOY")
redirect_uri = os.getenv('AZURE_REDIRECT_URI_PROD') if deploy == 'PROD' else os.getenv('AZURE_REDIRECT_URI_LOCAL')
port = 8000 if deploy == 'PROD' else 3000


################################
############ ROUTES ############
################################

@app.route('/')
async def login():
    return await render_template('login.html',client_id=CLIENT_ID,tenant_id=TENANT_ID)

@app.route('/textresponse')
async def textresponse():
    return await render_template('textresponse.html')


############ AUTH ############
@app.route('/auth/token-login', methods=['POST'])
async def token_login():

    """
    Authentication and user info saving
    """

    data = await request.get_json()
    id_token = data.get("id_token")
    access_token = data.get("access_token")

    async with aiohttp.ClientSession() as session_http:
        async with session_http.get(JWKS_URL) as jwks_resp:
            jwks = await jwks_resp.json()

    try:
        claims = jwt.decode(id_token, JsonWebKey.import_key_set(jwks), claims_options={
            "iss": {"essential": True, "value": f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"},
            "aud": {"essential": True, "value": CLIENT_ID},
        })
        claims.validate()
    except Exception as e:
        return jsonify({"error": "Invalid Token", "details": str(e)}), 401

    graph_headers = {'Authorization': f'Bearer {access_token}'}
    graph_url = 'https://graph.microsoft.com/v1.0/me?$select=displayName,mail,id'

    async with aiohttp.ClientSession() as session_http:
        async with session_http.get(graph_url, headers=graph_headers) as graph_resp:
            if graph_resp.status != 200:
                details = await graph_resp.text()
                return jsonify({"error": "MS Graph Error", "details": details}), 500
            user_data = await graph_resp.json()

    session['user'] = {
        "name": user_data.get("displayName"),
        "email": user_data.get("mail"),
        "oid": user_data.get("id")
    }

    user_key = f"user_{session['user']['oid']}"
    cache.set(user_key, session['user'], expire=300)

    return jsonify(session['user'])


########### USER ##########
@app.route('/me')
async def get_user():
    user = session.get("user")
    if not user:
        return jsonify({"error": "Authentication Failed"}), 401

    user_key = f"user_{user['oid']}"
    cached_user = await cache.get(user_key)

    if cached_user:
        return jsonify(cached_user)

    return jsonify(user)


######### GET GPT RESPONSE ##########
@app.route('/rispostaGPT', methods=['POST'])
async def rispostaGPT():

    """
    1. Retrieve user info.
    2. Set conversation context with "history"
    3. Search user query inside Azure Index
    4. Get and send result (Text response + Sharepoint file URL)
    """

    req_data = await request.get_json()
    user_reply = req_data.get("user_question", "")

    user = session.get("user")
    user_id = user.get("oid") if user else "anonymous"
    now = datetime.now()

    session_key = f"conversation_{user_id}_{now}"

    client = AzureOpenAI(
        api_key=os.getenv('AZURE_OPENAI_API_KEY'),  
        api_version="2024-10-21",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    deployment_name = os.getenv("DEPLOYMENT_NAME")


    session_data = cache.get(session_key) or {
        "history": []
    }

    azure_service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
    azure_key = os.getenv("AZURE_SEARCH_API_KEY")

    # Disable SSL verify in transport
    transport = RequestsTransport(connection_verify=False)

    search_client = SearchClient(
        endpoint=azure_service_endpoint,
        index_name="trial-index",
        credential=AzureKeyCredential(azure_key),
        # override
        transport=transport  
    )

    results = search_client.search(user_reply, top=3)

    results_output = [doc for doc in results]
    output = [url['text'] for url in results_output]
    output_webUrl = [url['webUrl'] for url in results_output]

    context = "\n\n".join(output)

    session_data['history'].append({"role": "user", "content": user_reply})

    system_prompt = f"""
                    You are an AI assistant. Respond only based on the documents below.
                    If an answer is not contained in the documents, say that you are not sure.
                    Documents:
                    {context}
                    """

    messages = [{"role": "system", "content": system_prompt}] + session_data['history']

    response = client.chat.completions.create(
        model=deployment_name,
        messages=messages,
        temperature=0.3,
        max_tokens=800
    )

    reply = response.choices[0].message.content + "\n\n" +  "Link utili:"

    session_data['history'].append({"role": "assistant", "content": reply})

    cache.set(session_key, session_data, expire=600)

    return jsonify({
        "success": True,
        "gpt_response": reply,
        "list_url": output_webUrl
    })


############ Run App ############
if __name__ == '__main__':
    if deploy == 'LOCAL':
        app.debug = True
        app.run(host='localhost', port=port)