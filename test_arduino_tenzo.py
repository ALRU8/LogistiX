import serial
import time

ser = serial.Serial('COM3', 9600, timeout=1)


def send_command_konveer(command):
    ser.write((command + '\n').encode('utf-8'))


def read_data_konveer():
    try:
        line = ser.readline().decode('utf-8').strip()
        if ',' in line:
            weight, distance = line.split(',')
            return float(weight), int(distance)
        return 0.0, 0
    except Exception as e:
        print(f"Ошибка при чтении данных: {e}")
        return None, None


def start_konveer():
    while True:
        send_command_konveer("start_motor")
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print(response)
            if response == "Command received":
                print("Команда получена.")
                break
        time.sleep(0.1)
    while True:
        line = ser.readline().decode('utf-8').strip()
        if line == "STOP":
            break
        else:
            pass


try:
    print("Отправка команды на запуск мотора...")
    start_konveer()
    print("Получение данных")
    weight, dist = read_data_konveer()
    while True:
        weight, dist = read_data_konveer()
        if weight is None or dist is None:
            pass
            weight = 0.0
            dist = 0
        else:
            print(f"Вес: {weight}, Расстояние: {dist}")

except KeyboardInterrupt:
    print("Программа завершена пользователем.")
finally:
    ser.close()
