from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from flask_restful import Api
import requests
import json
import hashlib
import time
import cv2
from robot_api import ArmController
import serial
import serial.serialutil
import serial.tools.list_ports
from host import *

tolerance = 5

app = Flask(__name__)
app.config['SECRET_KEY'] = "E:+x;*#--sDHlF'2lAJf33HXVoe3)NFMr[_y>7J_"
api = Api(app)

url = 'http://127.0.0.7:8888'

coords = {
    'x': 0,
    'y': 0,
    'z': 0
}

grabber = False

tablee = False

angle_1 = 70
angle_2 = 90

camera = cv2.VideoCapture(1)


def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    if 'username' in session:
        data = requests.get(url + '/api/v1/get/get_data_txt')
        print(data.json())
        return render_template('admin_panel.html', data=data.json())
    return redirect(url_for('login'))

@app.route('/test')
def test():
    if 'username' in session:
        data = requests.get(url + '/api/v1/get/get_data_txt')
        print(data.json())
        return render_template('test_panel.html', data=data.json())
    return redirect(url_for('login'))


@app.route('/login_error')
def login_error():
    return render_template('login_error.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        data_to_send = {
            'username': username
        }
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
    controller = ArmController()
    controller.connect("COM10", 115200)
    direction = request.json.get('direction')
    print(f'Moving {direction}')
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
    print(coords['x'])
    print(coords['y'])
    print(coords['z'])
    return jsonify({'status': 'success', 'direction': direction})


def send_servo_command(servo_type, value, servo_type_2, value_2):
    com_port = 'COM3'
    baud_rate = 9600
    try:
        arduino = serial.Serial(com_port, baud_rate, timeout=1)
        print(f"Connected to Arduino on {com_port}")
    except Exception as e:
        print(f"Error: {e}")
        exit()
    while True:
        command = f"{servo_type}:{value}\n{servo_type_2}:{value_2}\n"
        print(command)
        arduino.write(command.encode())
        response = arduino.readline().decode().strip()
        print('response: ', response)
        if 'Servo' in response:
            arduino.close()
            break



@app.route('/activate_grabber', methods=['POST'])
def activate_grabber():
    global grabber, angle_1, angle_2
    print('Grabber activated')
    if grabber:
        send_servo_command(1, 20, 2, angle_2)
        grabber = False
        angle_1 = 20
    else:
        send_servo_command(1, 70, 2, angle_2)
        grabber = True
        angle_1 = 70
    return jsonify({'status': 'success'})


@app.route('/table', methods=['POST'])
def table():
    global tablee, angle_1, angle_2
    print('Table activated')
    if tablee:
        send_servo_command(1, angle_1, 2, 90)
        tablee = False
        angle_2 = 90
        print('send_servo_command("fffrrrff", 90)')
    else:
        send_servo_command(1, angle_1, 2, 0)
        tablee = True
        angle_2 = 0
        print('send_servo_command("fffrrrff", )')
    return jsonify({'status': 'success'})


@app.route('/start_program', methods=['POST'])
def start_program():
    global tablee
    errorr = False
    print('Program started')
    controller = ArmController()
    controller.connect("COM10", 115200)
    send_servo_command(1, 70)
    send_servo_command(2, 90)
    controller.x_move_pos(-148, 800)
    controller.y_move_pos(168, 800)
    coords['x'] -= 148
    coords['y'] += 168
    while True:
        controller.position_timer()
        current_x = controller.wp_axe_x
        current_y = controller.wp_axe_y
        print(current_x, " ", current_y)

        if (abs(current_x - (-148)) < tolerance and
                abs(current_y - 168) < tolerance):
            break
        time.sleep(0.1)
    data = requests.get(url + '/api/v1/get/get_wall')
    fff = data.json()
    print("fff: ",fff)
    try:
        print(fff['error'])
        errorr = True
        if errorr:
            print('x: ', coords['x'], ' y: ', coords['y'], ' z: ', coords['z'])
            controller.y_move_pos(coords['y'] * -1, 800)
            controller.x_move_pos(coords['x'] * -1, 800)
            controller.rst_xyz()
            coords['x'] = 0
            coords['y'] = 0
            coords['z'] = 0
            while True:
                controller.position_timer()
                current_x = controller.wp_axe_x
                current_y = controller.wp_axe_y
                print(current_x, " ", current_y)

                if (abs(current_x - 0) < tolerance and
                        abs(current_y - 0) < tolerance):
                    break
                time.sleep(0.1)
            print('Программа завершена!')
        return jsonify({'status': 'success'})
    except:
        pass
    coordinates = fff['center']
    orientation = fff['orientation']
    x, y = coordinates
    print(x, " ", y, " ", orientation)
    data = requests.get(url + '/api/v1/get/get_size')
    fff = data.json()
    box_width = fff['box_width']
    box_height = fff['box_height']
    print(box_width, " ", box_height)
    # if orientation == 'вертикальная' and box_width == 8 and box_height == 4:
    #     if tablee:
    #         send_servo_command("fffrrrff", 555)
    #         tablee = False
    #     else:
    #         send_servo_command("fffrrrff", 333)
    #         tablee = True
    # if orientation == 'горизонтальная' and box_height == 8 and box_width == 4:
    #     if tablee:
    #         send_servo_command("fffrrrff", 555)
    #         tablee = False
    #     else:
    #         send_servo_command("fffrrrff", 333)
    #         tablee = True
    time.sleep(2)
    controller.y_move_pos(42, 800)
    coords['y'] += 42
    while True:
        controller.position_timer()
        current_x = controller.wp_axe_x
        current_y = controller.wp_axe_y
        print(current_x, " ", current_y)
        if (abs(current_x - (-150)) < tolerance and
                abs(current_y - 210) < tolerance):
            break
        time.sleep(0.1)
    time.sleep(3)
    controller.z_move_pos(-13, 800)
    coords['z'] -= 13
    while True:
        controller.position_timer()
        current_z = controller.wp_axe_z
        print(current_z, "z")
        if abs(current_z - (-3)) < 0.5:
            break
        time.sleep(0.1)
    time.sleep(2)
    send_servo_command(1, 70)
    if box_width == 4 and box_height == 4:
        send_servo_command(1, 30)
    if box_width == 8 and box_height == 4:
        send_servo_command(1, 38)
    if box_width == 4 and box_height == 8:
        send_servo_command(1, 30)
    controller.z_move_pos(13, 800)
    coords['z'] += 13
    while True:
        controller.position_timer()
        current_z = controller.wp_axe_z
        print(current_z, "z")

        if abs(current_z - 10) < 0.5:
            break
        time.sleep(0.1)
    time.sleep(1)
    print('x: ', coords['x'], ' y: ', coords['y'], ' z: ', coords['z'])
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
        print(current_x, " ", current_y)

        if (abs(current_x - 0) < tolerance and
                abs(current_y - 0) < tolerance):
            break
        time.sleep(0.1)
    controller.x_move_pos(x * -1, 800)
    controller.y_move_pos(y, 800)
    coords['x'] -= x
    coords['y'] += y
    while True:
        controller.position_timer()
        current_x = controller.wp_axe_x
        current_y = controller.wp_axe_y
        print(current_x, " ", current_y)

        if (abs(current_x - (x * -1)) < tolerance and
                abs(current_y - y) < tolerance):
            break
        time.sleep(0.1)
    controller.z_move_pos(-21, 800)
    coords['z'] -= 21
    while True:
        controller.position_timer()
        current_z = controller.wp_axe_z
        print(current_z, "z")
        if abs(current_z - (-21)) < 0.5:
            break
        time.sleep(0.1)
    time.sleep(1)
    send_servo_command(1, 45)
    time.sleep(1)
    controller.z_move_pos(21, 800)
    coords['z'] += 21
    while True:
        controller.position_timer()
        current_z = controller.wp_axe_z
        print(current_z, "z")
        if abs(current_z - 0) < 0.5:
            break
        time.sleep(0.1)
    time.sleep(3)
    print('x: ', coords['x'], ' y: ', coords['y'], ' z: ', coords['z'])
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
        print(current_x, " ", current_y)

        if (abs(current_x - 0) < tolerance and
                abs(current_y - 0) < tolerance):
            break
        time.sleep(0.1)
    print('Программа завершена!')
    return jsonify({'status': 'success'})


@app.route('/home', methods=['POST'])
def home():
    controller = ArmController()
    print('x: ', coords['x'], ' y: ', coords['y'], ' z: ', coords['z'])
    controller.connect("COM10", 115200)
    controller.x_move_pos(coords['x'] * -1, 800)
    controller.y_move_pos(coords['y'] * -1, 800)
    print('on  home')
    return jsonify({'status': 'success'})


@app.route('/reset', methods=['POST'])
def reset():
    controller = ArmController()
    controller.connect("COM10", 115200)
    controller.rst_xyz()
    coords['x'] = 0
    coords['y'] = 0
    coords['z'] = 0
    return jsonify({'status': 'success'})


@app.route('/get_data', methods=['GET'])
def get_data():
    data = requests.get(url + '/api/v1/get/get_data_txt')
    print(data.json())
    return jsonify(data.json())


def main():
    print('___STARTED____')
    api.add_resource(get_password, '/api/v1/get/get_password')
    api.add_resource(get_data_txt, '/api/v1/get/get_data_txt')
    api.add_resource(get_wall, '/api/v1/get/get_wall')
    api.add_resource(get_size, '/api/v1/get/get_size')
    app.run(host='127.0.0.7', port='8888', debug=True)


if __name__ == '__main__':
    main()
