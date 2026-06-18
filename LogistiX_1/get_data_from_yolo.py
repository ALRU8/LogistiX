import os

def read_from_file(file_path="output.txt"):
    if not os.path.exists(file_path):
        return "Файл с данными не найден."

    with open(file_path, "r", encoding="utf-8") as f:
        data = f.read()
    return data

if __name__ == "__main__":
    data = read_from_file()
    print("Информация из файла:")
    print(data)