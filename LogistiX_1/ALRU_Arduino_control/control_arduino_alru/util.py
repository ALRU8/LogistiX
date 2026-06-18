from __future__ import division, unicode_literals

import os
import sys
import threading
import time

import serial

from .boards import BOARDS


def get_the_board(layout=BOARDS["arduino"], base_dir="/dev/", identifier="tty.usbserial"):
    from .control_alru import Board
    boards = []
    for device in os.listdir(base_dir):
        if device.startswith(identifier):
            try:
                board = Board(os.path.join(base_dir, device), layout)
            except serial.SerialException:
                pass
            else:
                boards.append(board)
    if len(boards) == 0:
        raise IOError("No boards found in {0} with identifier {1}".format(base_dir, identifier))
    elif len(boards) > 1:
        raise IOError("More than one board found!")
    return boards[0]


class Iterator(threading.Thread):
    def __init__(self, board):
        super(Iterator, self).__init__()
        self.board = board
        self.daemon = True
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            try:
                while self.board.bytes_available():
                    self.board.iterate()
                time.sleep(0.001)
            except (AttributeError, serial.SerialException, OSError):
                break
            except Exception as e:
                if getattr(e, 'errno', None) == 9:
                    break
                try:
                    if e[0] == 9:
                        break
                except (TypeError, IndexError):
                    pass
                raise
            except KeyboardInterrupt:
                sys.exit()

    def stop(self):
        self.running = False


def to_two_bytes(integer):
    if integer > 32767:
        raise ValueError("Can't handle values bigger than 32767 (max for 2 bits)")
    return bytearray([integer % 128, integer >> 7])


def from_two_bytes(bytes):
    lsb, msb = bytes
    try:
        return msb << 7 | lsb
    except TypeError:
        try:
            lsb = ord(lsb)
        except TypeError:
            pass
        try:
            msb = ord(msb)
        except TypeError:
            pass
        return msb << 7 | lsb


def two_byte_iter_to_str(bytes):
    bytes = list(bytes)
    chars = bytearray()
    while bytes:
        lsb = bytes.pop(0)
        try:
            msb = bytes.pop(0)
        except IndexError:
            msb = 0x00
        chars.append(from_two_bytes([lsb, msb]))
    return chars.decode()


def str_to_two_byte_iter(string):
    bstring = string.encode()
    bytes = bytearray()
    for char in bstring:
        bytes.append(char)
        bytes.append(0)
    return bytes


def break_to_bytes(value):
    if value < 256:
        return (value,)
    c = 256
    least = (0, 255)
    for i in range(254):
        c -= 1
        rest = value % c
        if rest == 0 and value / c < 256:
            return (c, int(value / c))
        elif rest == 0 and value / c > 255:
            parts = list(break_to_bytes(value / c))
            parts.insert(0, c)
            return tuple(parts)
        else:
            if rest < least[1]:
                least = (c, rest)
    return (c, int(value / c))


def pin_list_to_board_dict(pinlist):
    board_dict = {
        "digital": [],
        "analog": [],
        "pwm": [],
        "servo": [],
        "disabled": [],
    }
    for i, pin in enumerate(pinlist):
        pin.pop()
        if not pin:
            board_dict["disabled"] += [i]
            board_dict["digital"] += [i]
            continue

        for j, _ in enumerate(pin):
            if j % 2 == 0:
                if pin[j:j + 4] == [0, 1, 1, 1]:
                    board_dict["digital"] += [i]

                if pin[j:j + 2] == [2, 10]:
                    board_dict["analog"] += [i]

                if pin[j:j + 2] == [3, 8]:
                    board_dict["pwm"] += [i]

                if pin[j:j + 2] == [4, 14]:
                    board_dict["servo"] += [i]

    diff = set(board_dict["digital"]) - set(board_dict["analog"])
    board_dict["analog"] = [n for n, _ in enumerate(board_dict["analog"])]

    board_dict["digital"] = [n for n, _ in enumerate(diff)]
    board_dict["servo"] = board_dict["digital"]

    board_dict = dict([
        (key, tuple(value))
        for key, value
        in board_dict.items()
    ])

    return board_dict