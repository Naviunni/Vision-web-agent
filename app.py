from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Event
import os
from agent import Agent

app = Flask(__name__)
socketio = SocketIO(app)

# Global state for the agent and user input
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
    # Run the agent's main loop in a background thread
    socketio.start_background_task(agent_instance.run, goal, socketio, user_input_event)

@socketio.on('user_response')
def handle_user_response(data):
    global user_response
    user_response = data['response']
    user_input_event.set() # Signal that user input has been received

if __name__ == '__main__':
    # Running without debug mode to prevent issues with the Playwright thread
    # and Werkzeug reloader.
    socketio.run(app, debug=False, allow_unsafe_werkzeug=True)