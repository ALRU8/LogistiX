from inference.core.interfaces.stream.sinks import render_boxes
import cv2
import supervision as sv
from pyzbar import pyzbar
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import torch
from ultralytics import YOLO

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

label_annotator = sv.LabelAnnotator()
box_annotator = sv.BoxAnnotator()

model = YOLO('yolov8n_custom_for_box.pt')
model.to(device)

def decode_qr_code(image, box):
    box_x = int(box['x'] - box['width'] / 2)
    box_y = int(box['y'] - box['height'] / 2)
    box_width = int(box['width'])
    box_height = int(box['height'])

    box_region = image[box_y:box_y + box_height, box_x:box_x + box_width]

    decoded_qr_codes = pyzbar.decode(box_region)

    if decoded_qr_codes:
        return decoded_qr_codes[0].data.decode("utf-8")
    else:
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

def my_custom_sink(video_frame):
    image = video_frame.imag.copy()

    height, width, _ = image.shape

    center_x = width // 2
    cv2.line(image, (center_x, 0), (center_x, height), (0, 255, 0), 2)

    output_data = ""

    results = model(image)

    boxes = []
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls)
            class_name = model.names[class_id]
            if class_name == "box":  # Filter for "lego" class
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append({
                    "class": class_name,
                    "x": (x1 + x2) / 2,
                    "y": (y1 + y2) / 2,
                    "width": x2 - x1,
                    "height": y2 - y1
                })

    if not boxes:
        print("No parcels detected.")
        output_data += "No parcels detected.\n"
    else:
        print(f"Количество посылок: {len(boxes)}")
        output_data += f"Количество посылок: {len(boxes)}\n"

        for i, box in enumerate(boxes):
            print(f"Посылка {i + 1}:")
            print(f"  Координаты: (x: {box['x']}, y: {box['y']})")
            print(f"  Размеры: (ширина: {box['width']}, высота: {box['height']})")

            output_data += f"Посылка {i + 1}:\n"
            output_data += f"  Координаты: (x: {box['x']}, y: {box['y']})\n"
            output_data += f"  Размеры: (ширина: {box['width']}, высота: {box['height']})\n"

            box_x = box['x']
            box_width = box['width']
            box_left = box_x - box_width / 2
            box_right = box_x + box_width / 2

            if box_left <= center_x <= box_right:
                print("OK")
                qr_code_value = decode_qr_code(image, box)
                if qr_code_value:
                    print("QR-код распознан.")
                    print(f"QR-код: {qr_code_value}")
                    output_data += f"  QR-код: {qr_code_value}\n"
                    image = draw_russian_text(image, f"QR: {qr_code_value}", (10, 30))
                else:
                    print("QR-код не распознан.")
                    output_data += "  QR-код не распознан.\n"
            else:
                print("Посылка не в центре.")
                output_data += "  Посылка не в центре.\n"

        detections = sv.Detections.from_yolov8(results[0])
        labels = [model.names[int(cls)] for cls in detections.class_id]
        image = label_annotator.annotate(scene=image, detections=detections, labels=labels)
        image = box_annotator.annotate(image, detections=detections)

    write_to_file(output_data)

    cv2.imshow("Predictions", image)
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
