import time
import cv2
from pyzbar import pyzbar
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def decode_qr_code(image):
    decoded_qr_codes = pyzbar.decode(image)

    qr_data = []
    for qr in decoded_qr_codes:
        qr_data.append({
            "data": qr.data.decode("utf-8"),
            "polygon": [(point.x, point.y) for point in qr.polygon]
        })

    return qr_data

def draw_russian_text(image, text, position, font_size=30, font_color=(0, 255, 0)):
    image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image_pil)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        print("Шрифт Arial не найден. Используется стандартный шрифт.")
        font = ImageFont.load_default()

    draw.text(position, text, font=font, fill=font_color)

    return cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)

def write_to_file(data, file_path="output.txt"):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data)


def enumerate_cameras(max_index=5):
    result = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            continue
        ret, frame = cap.read()
        cap.release()
        if ret:
            result.append(i)
    return result


def select_camera():
    available = enumerate_cameras(5)
    if not available:
        raise RuntimeError('Камера не найдена (индексы 0..4)')

    print("Найденные камеры:")
    for idx in available:
        print(f"{idx}: camera index={idx}")

    default = available[0]
    choice = input(f"Выберите индекс камеры из списка (по умолчанию {default}): ").strip()
    if not choice:
        return default

    if not choice.isdigit() or int(choice) not in available:
        print("Некорректный выбор, выбрана камера по умолчанию")
        return default

    return int(choice)


def my_custom_sink(video_frame):
    image = video_frame.copy()

    height, width, _ = image.shape

    center_x = width // 2
    cv2.line(image, (center_x, 0), (center_x, height), (0, 255, 0), 2)

    output_data = ""

    qr_codes = decode_qr_code(image)

    if not qr_codes:
        print("No QR codes detected.")
        output_data += "No QR codes detected.\n"
    else:
        print(f"Количество QR-кодов: {len(qr_codes)}")
        output_data += f"Количество QR-кодов: {len(qr_codes)}\n"

        for i, qr in enumerate(qr_codes):
            print(f"QR-код {i + 1}:")
            print(f"  Данные: {qr['data']}")

            output_data += f"QR-код {i + 1}:\n"
            output_data += f"  Данные: {qr['data']}\n"

            polygon = qr['polygon']
            x_coords = [point[0] for point in polygon]
            y_coords = [point[1] for point in polygon]

            qr_left = min(x_coords)
            qr_right = max(x_coords)
            qr_top = min(y_coords)
            qr_bottom = max(y_coords)

            qr_width = qr_right - qr_left
            qr_height = qr_bottom - qr_top

            output_data += f"  Координаты углов: {polygon}\n"
            output_data += f"  Размер области: ширина={qr_width}, высота={qr_height}\n"

            expanded_left = max(0, qr_left - 50)
            expanded_right = min(width, qr_right + 50)
            expanded_top = max(0, qr_top - 50)
            expanded_bottom = min(height, qr_bottom + 50)

            print("QR-код распознан.")
            output_data += "  QR-код распознан.\n"
            image = draw_russian_text(image, f"QR: {qr['data']}", (10, 30))

            pts = np.array([
                [expanded_left, expanded_top],
                [expanded_right, expanded_top],
                [expanded_right, expanded_bottom],
                [expanded_left, expanded_bottom]
            ], np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(image, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

    if qr_codes:
        write_to_file(output_data)

    cv2.imshow("QR Code Detection", image)
    cv2.waitKey(1)

from flask import Flask, Response

app = Flask(__name__)

camera_index = select_camera()
cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
if not cap.isOpened():
    raise RuntimeError(f"Не удалось открыть камеру index={camera_index}")

print(f"Используется камера index={camera_index} на порту 5000")


def generate_frames():
    while True:
        ret, frame = cap.read()
        if not ret:
            print('Не удалось получить кадр, попытка снова...')
            time.sleep(0.1)
            continue

        my_custom_sink(frame)

        ret2, buffer = cv2.imencode('.jpg', frame)
        if not ret2:
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/')
def camera_window():
    return """
        <!doctype html>
        <html lang='ru'>
            <head>
                <meta charset='utf-8'>
                <meta name='viewport' content='width=device-width, initial-scale=1.0'>
                <title>Camera Window</title>
                <style>
                    body { margin:0; padding:0; background:#111; color:#fff; font-family:Arial, sans-serif; }
                    .topbar { background:#0a0d10; color:#7fff7f; padding:10px 12px; text-align:center; }
                    .container { max-width:1280px; width:100%; margin:0 auto; }
                    .status { margin:8px auto; padding:8px 12px; background:#152022; border:1px solid #1f7f1f; border-radius:6px; font-size:14px; color:#bdecb5; }
                    .video-wrap { background:#000; border:2px solid #2f7f2f; border-radius:8px; overflow:hidden; }
                    img { width:100%; height:auto; display:block; }
                </style>
            </head>
            <body>
                <div class='topbar'>
                    <h1 style='margin:0; font-size:20px;'>Robot camera window | Сервер 5000</h1>
                </div>
                <div class='container'>
                    <div class='status'>
                        <strong>Camera index:</strong> %d | <strong>Рабочее состояние</strong> | <strong>QR-сканирование в поток</strong>
                    </div>
                    <div class='video-wrap'>
                        <img src='/video_feed' alt='Camera Stream' />
                    </div>
                    <div class='status'>
                        Нажмите <kbd>q</kbd> в консоли сервера для остановки, анимация с зеленой полосой и рамкой на кадре идет в реальном времени.
                    </div>
                </div>
            </body>
        </html>
    """ % camera_index


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
