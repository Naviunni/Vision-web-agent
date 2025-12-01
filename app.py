from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Event
import os
from agent import Agent

app = Flask(__name__)
socketio = SocketIO(app)

agent_instance = Agent()
user_input_event = Event()
user_response = None

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('start_task')
def handle_start_task(data):
    goal = data['goal']
    print(f"Received new task from user: {goal}")
    socketio.start_background_task(agent_instance.run, goal, socketio, user_input_event)

@socketio.on('user_response')
def handle_user_response(data):
    global user_response
    user_response = data['response']
    user_input_event.set()

if __name__ == '__main__':
    # Running without debug mode to prevent issues with the Playwright thread
    # and Werkzeug reloader.
    # Explicitly binding to 127.0.0.1 and port 5001 to resolve potential access issues.
    socketio.run(app, host='127.0.0.1', port=5001, debug=False, allow_unsafe_werkzeug=True)
