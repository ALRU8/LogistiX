from __future__ import division, unicode_literals
import inspect
import time
import warnings
import serial
import serial.tools.list_ports
from sys import platform
from .util import pin_list_to_board_dict, to_two_bytes, two_byte_iter_to_str, Iterator

DIGITAL_MESSAGE = 0x90
ANALOG_MESSAGE = 0xE0
DIGITAL_PULSE = 0x91
REPORT_ANALOG = 0xC0
REPORT_DIGITAL = 0xD0
START_SYSEX = 0xF0
SET_PIN_MODE = 0xF4
END_SYSEX = 0xF7
REPORT_VERSION = 0xF9
SYSTEM_RESET = 0xFF
QUERY_FIRMWARE = 0x79
EXTENDED_ANALOG = 0x6F
PIN_STATE_QUERY = 0x6D
PIN_STATE_RESPONSE = 0x6E
CAPABILITY_QUERY = 0x6B
CAPABILITY_RESPONSE = 0x6C
ANALOG_MAPPING_QUERY = 0x69
ANALOG_MAPPING_RESPONSE = 0x6A
SERVO_CONFIG = 0x70
STRING_DATA = 0x71
SHIFT_DATA = 0x75
I2C_REQUEST = 0x76
I2C_REPLY = 0x77
I2C_CONFIG = 0x78
REPORT_FIRMWARE = 0x79
SAMPLING_INTERVAL = 0x7A
SYSEX_NON_REALTIME = 0x7E
SYSEX_REALTIME = 0x7F

UNAVAILABLE = -1
INPUT = 0
OUTPUT = 1
ANALOG = 2
PWM = 3
SERVO = 4
INPUT_PULLUP = 11

DIGITAL = OUTPUT

BOARD_SETUP_WAIT_TIME = 5

class PinAlreadyTakenError(Exception):
    pass

class InvalidPinDefError(Exception):
    pass

class NoInputWarning(RuntimeWarning):
    pass

class Board(object):
    firmata_version = None
    firmware = None
    firmware_version = None
    _command_handlers = {}
    _command = None
    _stored_data = []
    _parsing_sysex = False
    AUTODETECT = None

    def __init__(self, port, layout=None, baudrate=57600, name=None, timeout=None, debug=False):
        if port == self.AUTODETECT:
            l = serial.tools.list_ports.comports()
            if l:
                if platform == "linux" or platform == "linux2":
                    for d in l:
                        if 'ACM' in d.device or 'usbserial' in d.device or 'ttyUSB' in d.device:
                            port = str(d.device)
                elif platform == "win32":
                    comports = []
                    for d in l:
                        if d.device:
                            if ("USB" in d.description) or (not d.description) or ("Arduino" in d.description):
                                devname = str(d.device)
                                comports.append(devname)
                    comports.sort()
                    if len(comports) > 0:
                        port = comports[0]
                else:
                    for d in l:
                        if d.vid:
                            port = str(d.device)
        if port == self.AUTODETECT:
            self.samplerThread = None
            self.sp = None
            raise Exception('Could not find a serial port.')
        if debug:
            print("Port=",port)
        self.samplerThread = Iterator(self)
        self.sp = serial.Serial(port, baudrate, timeout=timeout)
        self.__pass_time(BOARD_SETUP_WAIT_TIME)
        self.name = name
        self._layout = layout
        if not self.name:
            self.name = port
        if layout:
            self.setup_layout(layout)
        else:
            self.auto_setup()
        while self.bytes_available():
            self.iterate()

    def __str__(self):
        return "Board{0.name} on {0.sp.port}".format(self)

    def __del__(self):
        self.exit()

    def send_as_two_bytes(self, val):
        self.sp.write(bytearray([val % 128, val >> 7]))

    def setup_layout(self, board_layout):
        self.analog = []
        for i in board_layout['analog']:
            self.analog.append(Pin(self, i))
        self.digital = []
        self.digital_ports = []
        for i in range(0, len(board_layout['digital']), 8):
            num_pins = len(board_layout['digital'][i:i + 8])
            port_number = int(i / 8)
            self.digital_ports.append(Port(self, port_number, num_pins))
        for port in self.digital_ports:
            self.digital += port.pins
        for i in board_layout['pwm']:
            self.digital[i].PWM_CAPABLE = True
        for i in board_layout['disabled']:
            self.digital[i].mode = UNAVAILABLE
        self.taken = {'analog': dict(map(lambda p: (p.pin_number, False), self.analog)),
                      'digital': dict(map(lambda p: (p.pin_number, False), self.digital))}
        self._set_default_handlers()

    def _set_default_handlers(self):
        self.add_cmd_handler(ANALOG_MESSAGE, self._handle_analog_message)
        self.add_cmd_handler(DIGITAL_MESSAGE, self._handle_digital_message)
        self.add_cmd_handler(REPORT_VERSION, self._handle_report_version)
        self.add_cmd_handler(REPORT_FIRMWARE, self._handle_report_firmware)

    def samplingOn(self, sample_interval=19):
        if not self.samplerThread.running:
            if sample_interval < 1:
                raise ValueError("Sampling interval less than 1ms")
            self.setSamplingInterval(sample_interval)
            self.samplerThread.start()

    def samplingOff(self):
        if not self.samplerThread:
            return
        if self.samplerThread.running:
            self.samplerThread.stop()
            self.samplerThread.join()

    def auto_setup(self):
        self.add_cmd_handler(CAPABILITY_RESPONSE, self._handle_report_capability_response)
        self.send_sysex(CAPABILITY_QUERY, [])
        self.__pass_time(0.1)
        while self.bytes_available():
            self.iterate()
        if self._layout:
            self.setup_layout(self._layout)
        else:
            raise IOError("Board detection failed.")

    def add_cmd_handler(self, cmd, func):
        len_args = len(inspect.getfullargspec(func)[0])
        def add_meta(f):
            def decorator(*args, **kwargs):
                f(*args, **kwargs)
            decorator.bytes_needed = len_args - 1
            decorator.__name__ = f.__name__
            return decorator
        func = add_meta(func)
        self._command_handlers[cmd] = func

    def get_pin(self, pin_def):
        if type(pin_def) == list:
            bits = pin_def
        else:
            bits = pin_def.split(':')
        a_d = bits[0] == 'a' and 'analog' or 'digital'
        part = getattr(self, a_d)
        pin_nr = int(bits[1])
        if pin_nr >= len(part):
            raise InvalidPinDefError('Invalid pin definition: {0} at position 3 on {1}'
                                     .format(pin_def, self.name))
        if getattr(part[pin_nr], 'mode', None) == UNAVAILABLE:
            raise InvalidPinDefError('Invalid pin definition: '
                                     'UNAVAILABLE pin {0} at position on {1}'
                                     .format(pin_def, self.name))
        if self.taken[a_d][pin_nr]:
            raise PinAlreadyTakenError('{0} pin {1} is already taken on {2}'
                                       .format(a_d, bits[1], self.name))
        pin = part[pin_nr]
        self.taken[a_d][pin_nr] = True
        if pin.type is DIGITAL:
            if bits[2] == 'p':
                pin.mode = PWM
            elif bits[2] == 's':
                pin.mode = SERVO
            elif bits[2] == 'u':
                pin.mode = INPUT_PULLUP
            elif bits[2] == 'i':
                pin.mode = INPUT
            elif bits[2] == 'o':
                pin.mode = OUTPUT
            else:
                pin.mode = INPUT
        else:
            pin.enable_reporting()
        return pin

    def __pass_time(self, t):
        cont = time.time() + t
        while time.time() < cont:
            time.sleep(0)

    def send_sysex(self, sysex_cmd, data):
        msg = bytearray([START_SYSEX, sysex_cmd])
        msg.extend(data)
        msg.append(END_SYSEX)
        self.sp.write(msg)

    def bytes_available(self):
        return self.sp.inWaiting()

    def iterate(self):
        byte = self.sp.read()
        if not byte:
            return
        data = ord(byte)
        received_data = []
        handler = None
        if data < START_SYSEX:
            try:
                handler = self._command_handlers[data & 0xF0]
            except KeyError:
                return
            received_data.append(data & 0x0F)
            while len(received_data) < handler.bytes_needed:
                received_data.append(ord(self.sp.read()))
        elif data == START_SYSEX:
            data = ord(self.sp.read())
            handler = self._command_handlers.get(data)
            if not handler:
                return
            data = ord(self.sp.read())
            while data != END_SYSEX:
                received_data.append(data)
                data = ord(self.sp.read())
        else:
            try:
                handler = self._command_handlers[data]
            except KeyError:
                return
            while len(received_data) < handler.bytes_needed:
                received_data.append(ord(self.sp.read()))
        try:
            handler(*received_data)
        except ValueError:
            pass

    def get_firmata_version(self):
        return self.firmata_version

    def servo_config(self, pin, min_pulse=544, max_pulse=2400, angle=0):
        if pin > len(self.digital) or self.digital[pin].mode == UNAVAILABLE:
            raise IOError("Pin {0} is not a valid servo pin".format(pin))
        data = bytearray([pin])
        data += to_two_bytes(min_pulse)
        data += to_two_bytes(max_pulse)
        self.send_sysex(SERVO_CONFIG, data)
        self.digital[pin]._mode = SERVO
        self.digital[pin].write(angle)

    def setSamplingInterval(self, intervalInMs):
        data = to_two_bytes(int(intervalInMs))
        self.send_sysex(SAMPLING_INTERVAL, data)

    def exit(self):
        for a in self.analog:
            a.disable_reporting()
        for d in self.digital:
            d.disable_reporting()
        self.samplingOff()
        if hasattr(self, 'digital'):
            for pin in self.digital:
                if pin.mode == SERVO:
                    pin.mode = OUTPUT
        if hasattr(self, 'sp'):
            if self.sp:
                self.sp.close()

    def _handle_analog_message(self, pin_nr, lsb, msb):
        value = round(float((msb << 7) + lsb) / 1023, 4)
        try:
            if self.analog[pin_nr].reporting:
                self.analog[pin_nr].value = value
                if not self.analog[pin_nr].callback is None:
                    self.analog[pin_nr].callback(value)
        except IndexError:
            raise ValueError

    def _handle_digital_message(self, port_nr, lsb, msb):
        mask = (msb << 7) + lsb
        try:
            self.digital_ports[port_nr]._update(mask)
        except IndexError:
            raise ValueError

    def _handle_report_version(self, major, minor):
        self.firmata_version = (major, minor)

    def _handle_report_firmware(self, *data):
        major = data[0]
        minor = data[1]
        self.firmware_version = (major, minor)
        self.firmware = two_byte_iter_to_str(data[2:])

    def _handle_report_capability_response(self, *data):
        charbuffer = []
        pin_spec_list = []
        for c in data:
            if c == CAPABILITY_RESPONSE:
                continue
            charbuffer.append(c)
            if c == 0x7F:
                pin_spec_list.append(charbuffer[:])
                charbuffer = []
        self._layout = pin_list_to_board_dict(pin_spec_list)

class Port(object):
    def __init__(self, board, port_number, num_pins=8):
        self.board = board
        self.port_number = port_number
        self.reporting = False
        self.pins = []
        for i in range(num_pins):
            pin_nr = i + self.port_number * 8
            self.pins.append(Pin(self.board, pin_nr, type=DIGITAL, port=self))

    def __str__(self):
        return "Digital Port {0.port_number} on {0.board}".format(self)

    def enable_reporting(self):
        self.reporting = True
        msg = bytearray([REPORT_DIGITAL + self.port_number, 1])
        self.board.sp.write(msg)
        for pin in self.pins:
            if pin.mode == INPUT or pin.mode == INPUT_PULLUP:
                pin.reporting = True

    def disable_reporting(self):
        if not self.reporting:
            return
        self.reporting = False
        msg = bytearray([REPORT_DIGITAL + self.port_number, 0])
        self.board.sp.write(msg)

    def write(self):
        mask = 0
        for pin in self.pins:
            if pin.mode == OUTPUT:
                if pin.value == 1:
                    pin_nr = pin.pin_number - self.port_number * 8
                    mask |= 1 << int(pin_nr)
        msg = bytearray([DIGITAL_MESSAGE + self.port_number, mask % 128, mask >> 7])
        self.board.sp.write(msg)

    def _update(self, mask):
        if self.reporting:
            for pin in self.pins:
                if pin.mode is INPUT or pin.mode is INPUT_PULLUP:
                    pin_nr = pin.pin_number - self.port_number * 8
                    pin.value = (mask & (1 << pin_nr)) > 0
                    if not pin.callback is None:
                        pin.callback(pin.value)

class Pin(object):
    def __init__(self, board, pin_number, type=ANALOG, port=None):
        self.board = board
        self.pin_number = pin_number
        self.type = type
        self.port = port
        self.PWM_CAPABLE = False
        self._mode = (type == DIGITAL and OUTPUT or INPUT)
        self.reporting = False
        self.value = None
        self.callback = None

    def __str__(self):
        type = {ANALOG: 'Analog', DIGITAL: 'Digital'}[self.type]
        return "{0} pin {1}".format(type, self.pin_number)

    def _set_mode(self, mode):
        if mode is UNAVAILABLE:
            self._mode = UNAVAILABLE
            return
        if self._mode is UNAVAILABLE:
            raise IOError("{0} can not be used through Firmata".format(self))
        if mode is PWM and not self.PWM_CAPABLE:
            raise IOError("{0} does not have PWM capabilities".format(self))
        if mode == SERVO:
            if self.type != DIGITAL:
                raise IOError("Only digital pins can drive servos! {0} is not"
                              "digital".format(self))
            self._mode = SERVO
            self.board.servo_config(self.pin_number)
            return
        self._mode = mode
        self.board.sp.write(bytearray([SET_PIN_MODE, self.pin_number, mode]))
        if mode == INPUT or mode == INPUT_PULLUP:
            self.enable_reporting()

    def _get_mode(self):
        return self._mode

    mode = property(_get_mode, _set_mode)

    def enable_reporting(self):
        if self.mode is not INPUT and self.mode is not INPUT_PULLUP:
            raise IOError("{0} is not an input and can therefore not report".format(self))
        if self.type == ANALOG:
            self.reporting = True
            msg = bytearray([REPORT_ANALOG + self.pin_number, 1])
            self.board.sp.write(msg)
        else:
            self.port.enable_reporting()

    def disable_reporting(self):
        if self.type == ANALOG:
            if not self.reporting:
                return
            self.reporting = False
            msg = bytearray([REPORT_ANALOG + self.pin_number, 0])
            self.board.sp.write(msg)
        else:
            self.port.disable_reporting()

    def read(self):
        if self.mode == UNAVAILABLE:
            raise IOError("Cannot read pin {0}".format(self.__str__()))
        if (self.mode is INPUT) or (self.mode is INPUT_PULLUP) or (self.type == ANALOG):
            raise IOError("Reading via polling is not supported by this library. Please use the original pyfirmata.")
        return self.value

    def register_callback(self, _callback):
        self.callback = _callback

    def unregiser_callback(self):
        self.callback = None

    def write(self, value):
        if self.mode is UNAVAILABLE:
            raise IOError("{0} can not be used through Firmata".format(self))
        if self.mode is INPUT or self.mode is INPUT_PULLUP:
            raise IOError("{0} is set up as an INPUT and can therefore not be written to"
                          .format(self))
        if value is not self.value:
            self.value = value
            if self.mode is OUTPUT:
                if self.port:
                    self.port.write()
                else:
                    msg = bytearray([DIGITAL_MESSAGE, self.pin_number, value])
                    self.board.sp.write(msg)
            elif self.mode is PWM:
                value = int(round(value * 255))
                msg = bytearray([ANALOG_MESSAGE + self.pin_number, value % 128, value >> 7])
                self.board.sp.write(msg)
            elif self.mode is SERVO:
                value = int(value)
                msg = bytearray([ANALOG_MESSAGE + self.pin_number, value % 128, value >> 7])
                self.board.sp.write(msg)