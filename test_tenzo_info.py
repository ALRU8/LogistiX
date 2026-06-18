import serial
import time

ser_arduino = serial.Serial('COM3', 9600, timeout=1)

def read_data_konveer():
    try:
        line = ser_arduino.readline().decode('utf-8').strip()
        if ',' in line:
            weight, distance = line.split(',')
            if weight[0] == '.':
                weight = "0" + weight
            return float(weight), int(distance)
        return 0.0, 0
    except Exception as e:
        return None, None

def start_konveer():
    while True:
        send_command_konveer("start_motor")
        if ser_arduino.in_waiting > 0:
            response = ser_arduino.readline().decode('utf-8').strip()
            print(response)
            if response == "Command received":
                print("Команда получена.")
                break
        time.sleep(0.1)
    while True:
        line = ser_arduino.readline().decode('utf-8').strip()
        if line == "STOP":
            break
        else:
            pass

def send_command_konveer(command):
    ser_arduino.write((command + '\n').encode('utf-8'))


def write_to_file_tenzo(data_tenzo, file_path="tenzo.txt"):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(data_tenzo))

while True:
    file_1 = 'konveer_status.txt'
    with open(file_1, "r", encoding="utf-8") as f:
        data_1 = f.read()
    if data_1 == "Start":
        start_konveer()
        with open(file_1, "w", encoding="utf-8") as f:
            f.write("Stop")
    weight, dist = read_data_konveer()
    try:
        while weight < 2.0:
            weight, dist = read_data_konveer()
            if weight is None or dist is None:
                pass
                weight = 0.0
    except:
        weight = 0.0
    write_to_file_tenzo(weight)