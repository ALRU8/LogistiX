import cv2
import numpy as np
import torch
from pyzbar import pyzbar
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO


file = "YOLOV8s_Barcode_Detection.pt"
model = YOLO(file)


def decode_qr_from_region(image, x1, y1, x2, y2):
    h, w = image.shape[:2]
    pad = 10
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)
    region = image[y1:y2, x1:x2]
    decoded = pyzbar.decode(region)
    if decoded:
        return decoded[0].data.decode("utf-8")
    return None


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
        print(f"  {idx}: camera index={idx}")
    default = available[0]
    choice = input(f"Выберите индекс камеры из списка (по умолчанию {default}): ").strip()
    if not choice:
        return default
    if not choice.isdigit() or int(choice) not in available:
        print("Некорректный выбор, выбрана камера по умолчанию")
        return default
    return int(choice)


def my_custom_sink(image):
    output_data = ""

    results = model(image, verbose=False)

    detections = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            class_id = int(box.cls)
            class_name = model.names[class_id]
            conf = float(box.conf)
            detections.append({
                "class": class_name,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "conf": conf
            })

    if not detections:
        print("No QR codes detected.")
        output_data += "No QR codes detected.\n"
    else:
        print(f"Количество QR-кодов: {len(detections)}")
        output_data += f"Количество QR-кодов: {len(detections)}\n"

        for i, det in enumerate(detections):
            x1, y1, x2, y2 = det['x1'], det['y1'], det['x2'], det['y2']
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            qr_width = x2 - x1
            qr_height = y2 - y1

            print(f"QR-код {i + 1} [{det['class']} {det['conf']:.2f}]:")
            print(f"  Координаты: (x: {cx:.1f}, y: {cy:.1f})")
            print(f"  Размеры: (ширина: {qr_width}, высота: {qr_height})")

            output_data += f"QR-код {i + 1}:\n"
            output_data += f"  Данные: {det['class']}\n"
            output_data += f"  Координаты углов: [({x1},{y1}),({x2},{y1}),({x2},{y2}),({x1},{y2})]\n"
            output_data += f"  Размер области: ширина={qr_width}, высота={qr_height}\n"

            qr_data = decode_qr_from_region(image, x1, y1, x2, y2)
            if qr_data:
                print(f"  QR-код распознан: {qr_data}")
                output_data += "  QR-код распознан.\n"
                output_data += f"  Данные: {qr_data}\n"
                image = draw_russian_text(image, f"QR: {qr_data}", (10, 30 + i * 40))
            else:
                print("  Данные не считаны (pyzbar не смог декодировать).")
                output_data += "  QR-код не распознан.\n"

            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(image, f"{det['class']} {det['conf']:.2f}",
                        (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 255, 0), 2)

    write_to_file(output_data)

    cv2.imshow("QR Code Detection (YOLO)", image)
    cv2.waitKey(1)


if __name__ == "__main__":
    cam_index = select_camera()
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        my_custom_sink(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()