from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Event
import os
from agent import Agent

app = Flask(__name__)
socketio = SocketIO(app)

agent_instance = Agent()
shared_state = {
    "user_response": None,
    "user_input_event": Event(),
    "is_agent_running": False
}

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
    if shared_state["is_agent_running"]:
        socketio.emit('agent_response', {'data': "I am already running a task. Please wait."})
        return

    shared_state["is_agent_running"] = True
    agent_instance.reset() # Reset agent state for new task
    goal = data['goal']
    print(f"Received new task from user: {goal}")
    socketio.start_background_task(agent_instance.run, goal, socketio, shared_state)

@socketio.on('user_response')
def handle_user_response(data):
    if shared_state["is_agent_running"]:
        shared_state["user_response"] = data['response']
        shared_state["user_input_event"].set()

@socketio.on('task_finished')
def handle_task_finished():
    shared_state["is_agent_running"] = False
    print("Agent has finished the task.")


if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5001, debug=False, allow_unsafe_werkzeug=True)