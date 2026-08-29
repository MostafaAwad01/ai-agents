"""
socket_events.py — handles real-time chat messages using WebSockets.

WEBSOCKETS vs. HTTP:
  When you visit /resume, your browser makes one HTTP request and gets one
  HTML response — then the connection closes. That's how most web pages work.

  WebSockets are different: the connection stays open, like a phone call.
  Both sides (browser and server) can send messages at any time without
  making a new request. This is why the chat feels instant.

HOW EVENTS WORK:
  Instead of URL routes, WebSockets use named events:
    - Browser emits 'send_message'  →  server handles it here
    - Server emits 'receive_message' →  browser displays the reply

  The @socketio.on(...) decorator works just like @app.route(...) in Flask,
  but for WebSocket events instead of HTTP requests.
"""
from flask import current_app, session
from flask_socketio import emit
from flask_app import socketio
from flask_app.utils.llm import (
    handle_ai_chat_request,
    assess_message_risk,
    request_human_validation,
    handle_validation_response,
)


# db is attached to the Flask app instance by create_app() in __init__.py
# (app.db = db). Flask-SocketIO runs event handlers inside an app context,
# so current_app.db reaches that same shared instance here too -- no
# separate module-level variable needed.
#
# `session` (Homework 2) works here the same way: Flask-SocketIO ties its
# event handlers to the same signed session cookie the page's HTTP requests
# use, so state stashed here in one message (see request_human_validation
# in llm.py) is still there on the next.


@socketio.on('send_message')
def handle_message(data):
    user_message = data.get('message', '').strip()

    if not user_message:
        return

    try:
        db = current_app.db
        if session.get('pending_validation'):
            ai_response = handle_validation_response(db, user_message)
        elif assess_message_risk(user_message):
            ai_response = request_human_validation(user_message)
        else:
            ai_response = handle_ai_chat_request(db, role="Orchestrator", message=user_message)
    except Exception as error:
        print(f"LLM error: {error}")
        ai_response = "Sorry, something went wrong answering that."

    emit('receive_message', {'response': ai_response})
