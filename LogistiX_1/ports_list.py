import serial.tools.list_ports

def list_serial_ports():
    ports = serial.tools.list_ports.comports()

    if not ports:
        print("Нет доступных COM-портов.")
        return

    print(f"Найдено {len(ports)} COM-порт(ов):")
    for port in ports:
        print(f"Порт: {port.device}")
        print(f"  Описание: {port.description}")
        print(f"  Имя: {port.name}")
        print(f"  Производитель: {port.manufacturer}")
        print(f"  Серийный номер: {port.serial_number}")
        print(f"  Идентификатор оборудования: {port.hwid}")
        print(f"  Интерфейс: {port.interface}")
        print(f"  Расположение: {port.location}")
        print(f"  PID: {port.pid}, VID: {port.vid}")
        print("-" * 50)

if __name__ == "__main__":
    list_serial_ports()