from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from flask_restful import Api
import requests
import json
import hashlib
import time
import cv2
from ALRU_robot_api.robot_api_alru import ArmController
from ALRU_Arduino_control.control_arduino_alru import Arduino
from host import *
import serial
from dotenv import load_dotenv
import signal
import os

load_dotenv()

Secret_token = os.getenv('TOKEN')

tolerance = 5

app = Flask(__name__)
app.config['SECRET_KEY'] = Secret_token
api = Api(app)

url = 'http://127.0.0.1:8888'

coords = {
    'x': 0,
    'y': 0,
    'z': 0
}

grabber = False
tablee = False
konveer = True
angle_1 = 90
angle_2 = 90

# camera = cv2.VideoCapture(1)

board = Arduino('COM13')
servo_pin_1 = 8
servo_pin_2 = 11
servo_1 = board.get_pin(f'd:{servo_pin_1}:s')
servo_2 = board.get_pin(f'd:{servo_pin_2}:s')
ser = serial.Serial('COM3', 9600, timeout=1)


# def generate_frames():
#     while True:
#         success, frame = camera.read()
#         if not success:
#             break
#         else:
#             ret, buffer = cv2.imencode('.jpg', frame)
#             frame = buffer.tobytes()
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# @app.route('/video_feed')
# def video_feed():
#     return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_fields_state', methods=['GET'])
def get_fields_state():
    try:
        with open("fields_state.json", "r") as file:
            data = json.load(file)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({
            "field1": [[0]*8 for _ in range(12)],
            "field2": [[0]*8 for _ in range(12)]
        })

@app.route('/')
def index():
    if 'username' in session:
        data = requests.get(url + '/api/v1/get/get_data_txt')
        return render_template('admin_panel.html', data=data.json())
    return redirect(url_for('login'))


@app.route('/test')
def test():
    if 'username' in session:
        data = requests.get(url + '/api/v1/get/get_data_txt')
        return render_template('test_panel.html', data=data.json())
    return redirect(url_for('login'))


@app.route('/login_error')
def login_error():
    return render_template('login_error.html')


@app.route('/clear_field', methods=['POST'])
def clear_field():
    field_num = request.json.get('field')
    try:
        with open("fields_state.json", "r") as file:
            data = json.load(file)

        if field_num == 1:
            data['field1'] = [[0] * 8 for _ in range(12)]
            data['current_box_id'] = 3
        elif field_num == 2:
            data['field2'] = [[0] * 8 for _ in range(12)]
            data['current_box_id'] = 0

        with open("fields_state.json", "w") as file:
            json.dump(data, file)

        return jsonify({'status': 'success', 'update_fields': True})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/emergency_stop', methods=['POST'])
def emergency_stop():
    try:
        controller = ArmController()
        controller.connect("COM15", 115200)
        controller.x_move_pos(coords['x'] * -1, 800)
        controller.y_move_pos(coords['y'] * -1, 800)
        controller.rst_xyz()
    except:
        pass
    os.kill(os.getpid(), signal.SIGTERM)
    return jsonify({'status': 'success', 'message': 'Program terminated'})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        data_to_send = {'username': username}
        data = requests.get(url + '/api/v1/get/get_password', json=data_to_send)
        password_test = data.json()['key']
        hash_password = hashlib.sha512(password.encode()).hexdigest()
        if password_test == hash_password:
            session['username'] = username
            if username == 'test':
                return redirect(url_for('test'))
            else:
                return redirect(url_for('index'))
        return redirect(url_for('login_error'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/move', methods=['POST'])
def move():
    try:
        controller = ArmController()
        controller.connect("COM15", 115200)
    except:
        controller = ArmController()
        controller.disconnect()
        controller.connect("COM15", 115200)
    direction = request.json.get('direction')
    if direction == 'up':
        coords['z'] += 1
        controller.z_move_pos(1, 800)
    elif direction == 'down':
        coords['z'] -= 1
        controller.z_move_pos(-1, 800)
    elif direction == 'left':
        coords['x'] += 10
        controller.x_move_pos(10, 800)
    elif direction == 'right':
        coords['x'] -= 10
        controller.x_move_pos(-10, 800)
    elif direction == 'forward':
        coords['y'] += 10
        controller.y_move_pos(10, 150)
    elif direction == 'backward':
        coords['y'] -= 10
        controller.y_move_pos(-10, 150)
    return jsonify({'status': 'success', 'direction': direction})


def send_servo_command(servo_type, value, servo_type_2, value_2):
    if servo_type == 1:
        servo_1.write(value)
    if servo_type_2 == 2:
        servo_2.write(value_2)


@app.route('/activate_grabber', methods=['POST'])
def activate_grabber():
    global grabber, angle_1, angle_2
    if grabber:
        send_servo_command(1, 20, 2, angle_2)
        grabber = False
        angle_1 = 20
    else:
        send_servo_command(1, 90, 2, angle_2)
        grabber = True
        angle_1 = 90
    time.sleep(1)
    return jsonify({'status': 'success'})


@app.route('/table', methods=['POST'])
def table():
    global tablee, angle_1, angle_2
    if tablee:
        send_servo_command(1, angle_1, 2, 90)
        tablee = False
        angle_2 = 90
    else:
        send_servo_command(1, angle_1, 2, 0)
        tablee = True
        angle_2 = 0
    time.sleep(1)
    return jsonify({'status': 'success'})

@app.route('/reset_table', methods=['POST'])
def reset_table():
    file_path = "fields_state.json"
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Файл {file_path} удален.")
    with open(file_path, "w") as file:
        json.dump({"field1": [[0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]], "field2": [[0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]], "x1": 8, "y1": 12, "x2": 8, "y2": 12, "current_box_id": 0}, file)
        print(f"Файл {file_path} создан.")
    with open("fields_state.json", "r") as file:
        data = json.load(file)
    return jsonify({'status': 'success', 'update_fields': True, 'fields': data})


@app.route('/start_program', methods=['POST'])
def start_program():
    global tablee, angle_1, angle_2, konveer
    while True:
        konveer = False
        ser.write(("start_motor" + '\n').encode('utf-8'))
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print(response)
            if response == "Command received":
                print("Команда получена.")
                break
        time.sleep(0.1)
    konveer = True
    print('Program started')
    try:
        controller = ArmController()
        controller.connect("COM15", 115200)
    except:
        controller = ArmController()
        controller.disconnect()
        controller.connect("COM15", 115200)
    send_servo_command(1, 90, 2, 0)
    angle_1 = 90
    angle_2 = 0
    controller.x_move_pos(-73, 800)
    controller.y_move_pos(168, 800)
    coords['x'] -= 73
    coords['y'] += 168
    time.sleep(1)
    while True:
        controller.position_timer()
        current_x = controller.wp_axe_x
        current_y = controller.wp_axe_y
        if abs(current_x - (-73)) < tolerance and abs(current_y - 168) < tolerance:
            break
        time.sleep(0.1)
    data = requests.get(url + '/api/v1/get/get_wall')
    fff = data.json()
    print(fff)
    try:
        print(fff['error'])
        errorr = True
        if errorr:
            controller.y_move_pos(coords['y'] * -1, 800)
            controller.x_move_pos(coords['x'] * -1, 800)
            controller.rst_xyz()
            coords['x'] = 0
            coords['y'] = 0
            coords['z'] = 0
            time.sleep(1)
            while True:
                controller.position_timer()
                current_x = controller.wp_axe_x
                current_y = controller.wp_axe_y
                if abs(current_x - 0) < tolerance and abs(current_y - 0) < tolerance:
                    break
                time.sleep(0.1)
            print('Программа завершена!')
        return jsonify({'status': 'success'})
    except:
        pass
    coordinates = fff['center']
    orientation = fff['orientation']
    x, y = coordinates
    data = requests.get(url + '/api/v1/get/get_size')
    fff = data.json()
    box_width = fff['box_width']
    box_height = fff['box_height']
    pos_x_konv = 0
    pos_y_conv = 0
    if orientation == 'вертикальная':
        send_servo_command(1, angle_1, 2, 90)
        angle_2 = 90
    if orientation == 'вертикальная':
        pos_y_conv = 5
        pos_x_konv = 25
    else:
        pos_y_conv = 38
    time.sleep(1)
    controller.x_move_pos(pos_x_konv, 800)
    controller.y_move_pos(pos_y_conv, 800)
    coords['y'] += pos_y_conv
    coords['x'] += pos_x_konv
    while True:
        controller.position_timer()
        current_x = controller.wp_axe_x
        current_y = controller.wp_axe_y
        if abs(current_x - coords['x']) < tolerance and abs(current_y - coords['y']) < tolerance:
            break
        time.sleep(0.1)
    time.sleep(1)
    controller.z_move_pos(-36, 800)
    coords['z'] -= 36
    while True:
        controller.position_timer()
        current_z = controller.wp_axe_z
        print(current_z)
        if abs(current_z - (-45)) < 1:
            break
        time.sleep(0.1)
    time.sleep(1)
    send_servo_command(1, 20, 2, angle_2)
    angle_1 = 30
    time.sleep(1)
    controller.z_move_pos(36, 800)
    coords['z'] += 36
    while True:
        controller.position_timer()
        current_z = controller.wp_axe_z
        print(current_z)
        if abs(current_z - 9) < 1 or current_z >= -9:
            break
        time.sleep(0.1)
    time.sleep(1)
    controller.x_move_pos(coords['x'] * -1, 800)
    controller.y_move_pos(coords['y'] * -1, 800)
    controller.rst_xyz()
    coords['x'] = 0
    coords['y'] = 0
    coords['z'] = 0
    while True:
        controller.position_timer()
        current_x = controller.wp_axe_x
        current_y = controller.wp_axe_y
        if abs(current_x - 0) < tolerance and abs(current_y - 0) < tolerance:
            break
        time.sleep(0.1)
    time.sleep(1)
    controller.x_move_pos(x * -1, 800)
    controller.y_move_pos(y, 800)
    coords['x'] -= x
    coords['y'] += y
    while True:
        controller.position_timer()
        current_x = controller.wp_axe_x
        current_y = controller.wp_axe_y
        if abs(current_x - (x * -1)) < tolerance and abs(current_y - y) < tolerance:
            break
        time.sleep(0.1)
    time.sleep(1)
    controller.z_move_pos(-35, 800)
    coords['z'] -= 35
    while True:
        controller.position_timer()
        current_z = controller.wp_axe_z
        print(current_z)
        if abs(current_z - (-35)) < 1:
            break
        time.sleep(0.1)
    time.sleep(1)
    send_servo_command(1, 70, 2, angle_2)
    time.sleep(1)
    controller.z_move_pos(35, 800)
    coords['z'] += 35
    while True:
        controller.position_timer()
        current_z = controller.wp_axe_z
        print(current_z)
        if abs(current_z - 0) < 1 or current_z >= 0:
            break
        time.sleep(0.1)
    time.sleep(1)
    controller.x_move_pos(coords['x'] * -1, 800)
    controller.y_move_pos(coords['y'] * -1, 800)
    controller.rst_xyz()
    coords['x'] = 0
    coords['y'] = 0
    coords['z'] = 0
    while True:
        controller.position_timer()
        current_x = controller.wp_axe_x
        current_y = controller.wp_axe_y
        if abs(current_x - 0) < tolerance and abs(current_y - 0) < tolerance:
            break
        time.sleep(0.1)
    time.sleep(1)
    send_servo_command(1, 90, 2, 0)
    angle_1 = 90
    angle_2 = 0
    print('Программа завершена!')
    with open("fields_state.json", "r") as file:
        data = json.load(file)
    return jsonify({'status': 'success', 'update_fields': True, 'fields': data})


@app.route('/home', methods=['POST'])
def home():
    try:
        controller = ArmController()
        controller.connect("COM15", 115200)
    except:
        controller = ArmController()
        controller.disconnect()
        controller.connect("COM15", 115200)
    controller.x_move_pos(coords['x'] * -1, 800)
    controller.y_move_pos(coords['y'] * -1, 800)
    time.sleep(1)
    return jsonify({'status': 'success'})


@app.route('/reset', methods=['POST'])
def reset():
    try:
        controller = ArmController()
        controller.connect("COM15", 115200)
    except:
        controller = ArmController()
        controller.disconnect()
        controller.connect("COM15", 115200)
    controller.rst_xyz()
    coords['x'] = 0
    coords['y'] = 0
    coords['z'] = 0
    time.sleep(1)
    return jsonify({'status': 'success'})


@app.route('/get_data', methods=['GET'])
def get_data():
    weight = 0.0
    if konveer:
        ser.write(("info" + '\n').encode('utf-8'))
        try:
            line = ser.readline().decode('utf-8').strip()
            if ',' in line:
                weight, distance = line.split(',')
                if weight[0] == '.':
                    weight = "0" + weight
                try:
                    weight = float(weight)
                except:
                    weight = 0.0
        except:
            weight = 0.0
    file_1 = 'tenzo.txt'
    with open(file_1, "w", encoding="utf-8") as f:
        f.write(str(weight))
    print(weight)
    data = requests.get(url + '/api/v1/get/get_data_txt')
    return jsonify(data.json())


def main():
    api.add_resource(get_password, '/api/v1/get/get_password')
    api.add_resource(get_data_txt, '/api/v1/get/get_data_txt')
    api.add_resource(get_wall, '/api/v1/get/get_wall')
    api.add_resource(get_size, '/api/v1/get/get_size')
    app.run(host='127.0.0.1', port='8888', debug=True, use_reloader=False)


if __name__ == '__main__':
    main()
