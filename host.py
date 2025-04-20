from flask import jsonify, request
from flask_restful import Resource
from json import loads
from database import db
import os
import re
import json
from math import trunc, ceil

class get_password(Resource):
    def get(self):
        try:
            data = loads(request.data)
            print(data)
            username = data['username']
            password = db.get_user_password(username)
            print(username, " ", password)
            return jsonify({'key': password})
        except Exception as e:
            return jsonify({'key': e})

class add_user(Resource):
    def post(self):
        try:
            data = loads(request.data)
            username = data['username']
            password = data['password']
            db.add_user(username, password)
            return jsonify({'key': 'success'})
        except Exception as e:
            return jsonify({'key': e})

class get_data_txt(Resource):
    def get(self):
        try:
            file = 'output.txt'
            if not os.path.exists(file):
                return "Файл с данными не найден."
            with open(file, "r", encoding="utf-8") as f:
                data = f.read()
            file_1 = 'tenzo.txt'
            if not os.path.exists(file_1):
                return "Файл с данными не найден."
            with open(file_1, "r", encoding="utf-8") as f:
                data_1 = f.read()
            data += f"\nВес товара: {data_1}\n"
            return jsonify({'text': data})
        except Exception as e:
            return jsonify({'key': e})

class get_size(Resource):
    def get(self):
        try:
            def extract_qr_data_lines(file_path):
                pattern = r"Поле:\s*\d+\s*Ширина:\s*\d+\s*Высота:\s*\d+"
                qr_data_lines = []
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()

                        matches = re.findall(pattern, content)

                        qr_data_lines.extend(matches)
                except FileNotFoundError:
                    print(f"Файл {file_path} не найден.")
                except Exception as e:
                    print(f"Произошла ошибка: {e}")

                return qr_data_lines

            x1, y1 = 8, 12
            x2, y2 = 8, 12
            file_path = "output.txt"
            qr_data_lines = extract_qr_data_lines(file_path)
            print(qr_data_lines)
            pattern = r"Поле:\s*(\d+)\s*Ширина:\s*(\d+)\s*Высота:\s*(\d+)"
            match = re.match(pattern, qr_data_lines[0])
            if not match:
                print("Некорректный формат входных данных.")
                return None
            target_field = int(match.group(1))
            box_width = int(match.group(2))
            box_height = int(match.group(3))
            return jsonify({'box_width': box_width, 'box_height': box_height})
        except Exception as e:
            return jsonify({'key': e})

class get_wall(Resource):
    def get(self):
        try:
            field1 = []
            field2 = []

            def create_field(width, height):
                return [[0 for _ in range(width)] for _ in range(height)]

            def print_field(field, field_name):
                print(f"Текущее состояние поля {field_name}:")
                for row in field:
                    print(' '.join(map(str, row)))
                print()

            def can_place_box(field, box_width, box_height, x, y):
                if x + box_width > len(field[0]) or y + box_height > len(field):
                    return False
                for i in range(y, y + box_height):
                    for j in range(x, x + box_width):
                        if field[i][j] != 0:
                            return False
                return True

            def place_box(field, box_width, box_height, x, y, box_id):
                for i in range(y, y + box_height):
                    for j in range(x, x + box_width):
                        field[i][j] = box_id

            def calculate_score(field, box_width, box_height, x, y):
                score = 0
                for i in range(y, y + box_height):
                    row_filled = sum(1 for cell in field[i] if cell != 0)
                    score += row_filled
                for j in range(x, x + box_width):
                    column_filled = sum(1 for i in range(len(field)) if field[i][j] != 0)
                    score += column_filled
                for i in range(y, y + box_height):
                    for j in range(x, x + box_width):
                        if i > 0 and field[i - 1][j] != 0:
                            score += 1
                        if i < len(field) - 1 and field[i + 1][j] != 0:
                            score += 1
                        if j > 0 and field[i][j - 1] != 0:
                            score += 1
                        if j < len(field[0]) - 1 and field[i][j + 1] != 0:
                            score += 1
                edge_bonus = 0
                edge_bonus += (len(field) - (y + box_height))
                edge_bonus += x
                edge_bonus += (len(field[0]) - (x + box_width))
                score += edge_bonus * 2
                return score

            def find_best_placement(field, box_width, box_height):
                best_x, best_y, best_score = -1, -1, -1
                best_orientation = None

                if box_height >= box_width:
                    width, height = box_width, box_height
                    for y in range(len(field) - height + 1):
                        for x in range(len(field[0]) - width + 1):
                            if can_place_box(field, width, height, x, y):
                                score = calculate_score(field, width, height, x, y)
                                score += 200
                                if score > best_score:
                                    best_score = score
                                    best_x, best_y = x, y
                                    best_orientation = (width, height)
                else:

                    width, height = box_height, box_width
                    for y in range(len(field) - height + 1):
                        for x in range(len(field[0]) - width + 1):
                            if can_place_box(field, width, height, x, y):
                                score = calculate_score(field, width, height, x, y)
                                score += 200
                                if score > best_score:
                                    best_score = score
                                    best_x, best_y = x, y
                                    best_orientation = (width, height)

                if best_orientation is None:
                    width, height = box_width, box_height
                    for y in range(len(field) - height + 1):
                        for x in range(len(field[0]) - width + 1):
                            if can_place_box(field, width, height, x, y):
                                score = calculate_score(field, width, height, x, y)
                                if score > best_score:
                                    best_score = score
                                    best_x, best_y = x, y
                                    best_orientation = (width, height)

                return best_x, best_y, best_orientation

            def is_field_full(field):
                for row in field:
                    if 0 in row:
                        return False
                return True

            def calculate_center(size):
                if size % 2 == 0:
                    return (size // 2) + 0.5
                else:
                    return size // 2 + 1

            def save_fields_to_file(field1, field2, x1, y1, x2, y2, current_box_id, filename="fields_state.json"):
                state = {
                    "field1": field1,
                    "field2": field2,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "current_box_id": current_box_id
                }
                with open(filename, "w") as file:
                    json.dump(state, file)

            def load_fields_from_file(x1, y1, x2, y2, filename="fields_state.json"):
                try:
                    with open(filename, "r") as file:
                        state = json.load(file)
                        if state["x1"] == x1 and state["y1"] == y1 and state["x2"] == x2 and state["y2"] == y2:
                            return state["field1"], state["field2"], state.get("current_box_id", 0)
                except FileNotFoundError:
                    pass
                return None, None, 0

            def process_input(input_string, x1, y1, x2, y2):
                global field1, field2

                pattern = r"Поле:\s*(\d+)\s*Ширина:\s*(\d+)\s*Высота:\s*(\d+)"
                match = re.match(pattern, input_string)
                if not match:
                    print("Некорректный формат входных данных.")
                    return None

                target_field = int(match.group(1))
                box_width = int(match.group(2))
                box_height = int(match.group(3))

                field1, field2, current_box_id = load_fields_from_file(x1, y1, x2, y2)

                if not field1:
                    field1 = create_field(x1, y1)
                if not field2:
                    field2 = create_field(x2, y2)

                field = field1 if target_field == 1 else field2
                field_name = "1" if target_field == 1 else "2"

                x, y, orientation = find_best_placement(field, box_width, box_height)
                if x != -1 and y != -1:
                    has_left = any(field[i][x - 1] != 0 for i in range(y, y + orientation[1])) if x > 0 else False
                    has_top = any(field[y - 1][j] != 0 for j in range(x, x + orientation[0])) if y > 0 else False

                    width, height = orientation
                    current_box_id += 1
                    place_box(field, width, height, x, y, current_box_id)

                    t1 = False
                    t2 = False

                    if width % 2 == 0:
                        t1 = True
                    if height % 2 == 0:
                        t2 = True

                    center_x_cell = x + ceil(width / 2)
                    center_y_cell = y + ceil(height / 2)

                    center_x_cm = center_x_cell
                    center_y_cm = center_y_cell

                    if width > height:
                        orientation_str = "горизонтальная"
                    elif width < height:
                        orientation_str = "вертикальная"
                    else:
                        orientation_str = "квадратная"

                    print(f"Ориентация коробки: {orientation_str}")
                    print(f"Центр коробки на поле {field_name} (клетки): ({center_x_cell}, {center_y_cell})")
                    print(f"Центр коробки на поле {field_name} в сантиметрах: ({center_x_cm} см, {center_y_cm} см)")

                    print("Итоговое состояние полей:")
                    print_field(field1, "1")
                    print_field(field2, "2")

                    save_fields_to_file(field1, field2, x1, y1, x2, y2, current_box_id)
                    if t1:
                        center_x_cm += 0.5
                    if t2:
                        center_y_cm += 0.5

                    center_xx = 38 + (center_x_cm * 8)
                    center_yy = 96 - (center_y_cm * 8)

                    if field_name == "2":
                        center_xx += 144

                    if has_left and has_top:
                        center_xx += 4
                        center_yy -= 4
                        print('has_left and has_top')
                    elif has_left:
                        center_xx += 4
                        print('has_left')
                    elif has_top:
                        center_yy -= 4
                        print('has_top')
                    else:
                        print('NOT has_left and has_top')

                    return {
                        "center_coordinates": [center_xx, center_yy],
                        "orientation": orientation_str
                    }
                else:
                    print(f"Коробка размером {box_width}x{box_height} не помещается в поле {field_name}.")
                    return None

            def extract_qr_data_lines(file_path):
                pattern = r"Поле:\s*\d+\s*Ширина:\s*\d+\s*Высота:\s*\d+"
                qr_data_lines = []
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()

                        matches = re.findall(pattern, content)

                        qr_data_lines.extend(matches)
                except FileNotFoundError:
                    print(f"Файл {file_path} не найден.")
                except Exception as e:
                    print(f"Произошла ошибка: {e}")

                return qr_data_lines

            x1, y1 = 8, 12
            x2, y2 = 8, 12
            file_path = "output.txt"
            qr_data_lines = extract_qr_data_lines(file_path)
            if not qr_data_lines:
                while not qr_data_lines:
                    try:
                        qr_data_lines = extract_qr_data_lines(file_path)
                    except:
                        pass
            print(qr_data_lines)
            data = process_input(qr_data_lines[0], x1, y1, x2, y2)
            if data is None:
                return jsonify({'error': "error"})
            center_coordinates = data['center_coordinates']
            orientation_str = data['orientation']
            print(center_coordinates)
            print(orientation_str)
            return jsonify({'center': center_coordinates, 'orientation': orientation_str})
        except Exception as e:
            return jsonify({'key': str(e)})