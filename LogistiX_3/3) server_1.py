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

            if expanded_left <= center_x <= expanded_right:
                print("QR-код в центре.")
                output_data += "  QR-код в центре.\n"
                image = draw_russian_text(image, f"QR: {qr['data']}", (10, 30))
            else:
                print("QR-код не в центре.")
                output_data += "  QR-код не в центре.\n"

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

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    my_custom_sink(frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()