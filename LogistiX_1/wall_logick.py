import re
import json
from math import trunc, ceil

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

    vertical_bonus = 100

    for orientation in [(box_height, box_width), (box_width, box_height)]:
        width, height = orientation
        for y in range(len(field) - height + 1):
            for x in range(len(field[0]) - width + 1):
                if can_place_box(field, width, height, x, y):
                    score = calculate_score(field, width, height, x, y)

                    if orientation == (box_height, box_width):
                        score += vertical_bonus

                    if score > best_score:
                        best_score = score
                        best_x, best_y = x, y
                        best_orientation = orientation

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

    pattern = r"Поле:\s*(\d+)\s*Ширина:\s*(\d+)\s*Высота:\s*(\d+)\s*Вес:\s*(\d+)"
    match = re.match(pattern, input_string)
    if not match:
        print("Некорректный формат входных данных.")
        return None

    target_field = int(match.group(1))
    box_width = int(match.group(2))
    box_height = int(match.group(3))
    weight = int(match.group(4))

    field1, field2, current_box_id = load_fields_from_file(x1, y1, x2, y2)

    if not field1:
        field1 = create_field(x1, y1)
    if not field2:
        field2 = create_field(x2, y2)

    field = field1 if target_field == 1 else field2
    field_name = "1" if target_field == 1 else "2"

    x, y, orientation = find_best_placement(field, box_width, box_height)
    if x != -1 and y != -1:
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

        orientation_str = "горизонтальная" if orientation == (box_width, box_height) else "вертикальная"
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

        center_xx = 40 + (center_x_cm * 8)
        center_yy = 92 - (center_y_cm * 8)

        if field_name == "2":
            center_xx += 144
        return {
            "center_coordinates": [center_xx, center_yy],
            "orientation": orientation_str
        }
    else:
        print(f"Коробка размером {box_width}x{box_height} не помещается в поле {field_name}.")
        return None


def extract_qr_data_lines(file_path):
    pattern = r"Поле:\s*\d+\s*Ширина:\s*\d+\s*Высота:\s*\d+\s*Вес:\s*\d+"

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

if __name__ == "__main__":
    x1, y1 = 8, 12
    x2, y2 = 8, 12
    file_path = "output.txt"
    qr_data_lines = extract_qr_data_lines(file_path)
    print(qr_data_lines)
    input_string = "Поле: 2 Ширина: 4 Высота: 4 Вес: 12"
    data = process_input(qr_data_lines[0], x1, y1, x2, y2)
    center_coordinates = data['center_coordinates']
    orientation_str = data['orientation']


    if center_coordinates:
        print(f"Координаты центра коробки в сантиметрах: {center_coordinates}\nОриентация: {orientation_str}")