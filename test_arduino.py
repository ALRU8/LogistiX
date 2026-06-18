import serial
import time

try:
    ser = serial.Serial('COM3', 9600, timeout=1)
    time.sleep(2)
except serial.SerialException as e:
    print(f"Ошибка при подключении к порту: {e}")
    exit()

def send_servo_command(servo_type, value):

    try:
        command = f"{servo_type}:{value}\n"
        ser.write(command.encode())
        print(f"Отправлено: {command.strip()}")
    except serial.SerialException as e:
        print(f"Ошибка при отправке команды: {e}")

try:
    while True:
        angle = int(input("Введите угол для первого сервопривода (0-180): "))
        send_servo_command("servo1", angle)

        binary_value = int(input("Введите значение для второго сервопривода (0 или 1): "))
        send_servo_command("servo2", binary_value)

except KeyboardInterrupt:
    print("Программа завершена")
finally:
    ser.close()