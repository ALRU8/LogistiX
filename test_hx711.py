from pyfirmata2 import Arduino
import struct
import time

PORT = 'COM5'

class WeightReader:
    def __init__(self, port):
        self.board = Arduino(port)
        self.board.samplingOn()
        self.board.add_cmd_handler(
            0x71,
            self._handle_weight_data
        )
        self.weight = 0.0

    def _handle_weight_data(self, data):
        try:
            self.weight = struct.unpack('<f', bytes(data))[0]
        except Exception as e:
            print(f"Ошибка при обработке данных: {e}")

    def read(self):
        return self.weight

    def close(self):
        self.board.exit()

if __name__ == "__main__":
    reader = WeightReader(PORT)
    try:
        while True:
            print(f"Вес: {reader.read():.2f} г")
            time.sleep(0.5)
    except KeyboardInterrupt:
        reader.close()
        print("Соединение закрыто")