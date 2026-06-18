import serial
import serial.serialutil
import serial.tools.list_ports
import time

class ArmController:
    def __init__(self):
        self.serial = None
        self.wp_axe_x = 0.0
        self.wp_axe_y = 0.0
        self.wp_axe_z = 0.0
        self.mp_axe_x = 0.0
        self.mp_axe_y = 0.0
        self.mp_axe_z = 0.0

    def is_connected(self):
        return self.serial is not None and self.serial.is_open

    def get_line(self):
        data = self.serial.readline()
        return data.decode("utf-8")

    def get_lines(self):
        lines = []
        while self.serial.inWaiting() > 0:
            line = self.get_line()
            lines.append(line)
        return lines

    def connect(self, port, baudrate):
        try:
            self.serial = serial.Serial(port, int(baudrate))
            while True:
                line = self.get_line()
                if line.endswith(" ['$' for help]\r\n"):
                    break
        except serial.serialutil.SerialException as e:
            try:
                self.serial.close()
                self.serial = None
            except:
                pass
            print(f"Can't connect to {port}: {str(e)}")

    def disconnect(self):
        if self.serial:
            self.serial.close()
            self.serial = None

    def serial_list(self):
        serial_ports = []
        for p in serial.tools.list_ports.comports():
            serial_ports.append(p[0])
        return serial_ports

    def _send_command(self, g_code):
        self.serial.write("{}\r\n".format(g_code).encode('utf-8'))
        self.serial.flushInput()
        lines = []
        while True:
            line = self.get_line()
            if line == 'ok\r\n':
                break
            lines.append(line)
        return lines

    def alarm(self):
        return self._send_command('$X')

    def parser_state(self):
        return self._send_command('$G')

    def infos(self):
        return self._send_command('$$')

    def cycle_start(self):
        return self._send_command("~")

    def feed_hold(self):
        return self._send_command("!")

    def rst_xyz(self):
        return self._send_command("G92X0Y0Z0")

    def rst_x(self):
        return self._send_command("G92 X0")

    def rst_y(self):
        return self._send_command("G92 Y0")

    def rst_z(self):
        return self._send_command("G92 Z0")

    def home(self):
        return self._send_command("G90X0Y0Z0")

    def x_move_pos(self, value, speed):
        return self._send_command(f"G91X{value}F{speed}")

    def x_move_neg(self, value, speed):
        return self._send_command(f"G91X-{value}F{speed}")

    def y_move_pos(self, value, speed):
        return self._send_command(f"G91Y{value}F{speed}")

    def y_move_neg(self, value, speed):
        return self._send_command(f"G91Y-{value}F{speed}")

    def z_move_pos(self, value, speed):
        return self._send_command(f"G91Z{value}F{speed}")

    def z_move_neg(self, value, speed):
        return self._send_command(f"G91Z-{value}F{speed}")

    def send_full_command(self, command):
        return self._send_command(f"{command}")

    def save_pos(self, speed):
        self.position_timer()
        return f"G01X{self.wp_axe_x}Y{self.wp_axe_y}Z{self.wp_axe_z}F{speed}"

    def position_timer(self):
        if not self.is_connected():
            return

        result = self._send_command("?")
        if len(result) != 1:
            return

        response = result[0].strip("<>\r\n")
        parts = response.split(":")

        if len(parts) >= 2:
            maxes = parts[1]
            waxes = parts[2] if len(parts) > 2 else maxes

            m_details = maxes.split(",")
            w_details = waxes.split(",")

            if len(m_details) >= 3:
                self.mp_axe_x = float(m_details[0])
                self.mp_axe_y = float(m_details[1])
                self.mp_axe_z = float(m_details[2])

            if len(w_details) >= 3:
                self.wp_axe_x = float(w_details[0])
                self.wp_axe_y = float(w_details[1])
                self.wp_axe_z = float(w_details[2])
