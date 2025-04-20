from plantuml import PlantUML
import os

uml_diagram = """
@startuml
!theme mars
skinparam shadowing false
skinparam linetype ortho
skinparam component {
    BackgroundColor White
    BorderColor Black
    ArrowFontColor Black
}
skinparam package {
    BackgroundColor LightBlue
    BorderColor Black
    ArrowFontColor Black
}
skinparam node {
    BackgroundColor LightGreen
    BorderColor Black
    ArrowFontColor Black
}
skinparam database {
    BackgroundColor LightYellow
    BorderColor Black
    ArrowFontColor Black
}
skinparam usecase {
    BackgroundColor LightGray
    BorderColor Black
    ArrowFontColor Black
}

left to right direction

package "Web Application" #LightBlue {
    [Flask App] as FlaskApp
    [Admin Panel] as AdminPanel
    [Test Panel] as TestPanel
    [Login System] as LoginSystem

    FlaskApp --> AdminPanel
    FlaskApp --> TestPanel
    FlaskApp --> LoginSystem
}

package "API Endpoints" #LightGreen {
    [Move Robot Arm] as MoveArm
    [Activate Grabber] as ActivateGrabber
    [Table Control] as TableControl
    [Start Program] as StartProgram
    [Home Position] as HomePosition
    [Reset Position] as ResetPosition
    [Get Data] as GetData

    FlaskApp --> MoveArm
    FlaskApp --> ActivateGrabber
    FlaskApp --> TableControl
    FlaskApp --> StartProgram
    FlaskApp --> HomePosition
    FlaskApp --> ResetPosition
    FlaskApp --> GetData
}

package "Robot Control" #LightYellow {
    [ArmController] as ArmController
    [Servo Control] as ServoControl
    [Arduino Board] as ArduinoBoard

    MoveArm --> ArmController
    ActivateGrabber --> ServoControl
    TableControl --> ServoControl
    StartProgram --> ArmController
    StartProgram --> ServoControl
    HomePosition --> ArmController
    ResetPosition --> ArmController

    ServoControl --> ArduinoBoard
    ArmController --> ArduinoBoard
}

package "Video Processing" #LightCyan {
    [YOLO Model] as YOLOModel
    [QR Code Decoder] as QRDecoder
    [Video Feed] as VideoFeed

    FlaskApp --> VideoFeed
    VideoFeed --> YOLOModel
    YOLOModel --> QRDecoder
}

package "Database" #LightPink {
    [User Database] as UserDB
    [Data Storage] as DataStorage

    LoginSystem --> UserDB
    GetData --> DataStorage
}

package "Logic Processing" #LightGray {
    [Box Placement Logic] as BoxLogic
    [Field Management] as FieldManager

    StartProgram --> BoxLogic
    BoxLogic --> FieldManager
}

FlaskApp --> (Port 8888)
VideoFeed --> (Camera)
ArduinoBoard --> (COM3)
UserDB --> (DataBase.db)

note right of FlaskApp #White
Main web application running on:
- Port: 8888
- Host: 127.0.0.1
Handles all HTTP requests
and coordinates between
components
end note

note bottom of YOLOModel #White
Handles object detection:
- Detects boxes
- Decodes QR codes
- Writes data to output.txt
end note

note right of BoxLogic #White
Implements complex logic for:
- Box placement
- Field optimization
- Orientation handling
end note

note left of ArmController #White
Controls robot arm movements:
- X, Y, Z axis control
- Position tracking
- Movement validation
end note
@enduml
"""


def create_uml_diagram():
    try:
        os.makedirs("temp", exist_ok=True)

        with open("temp/diagram.puml", "w", encoding="utf-8") as file:
            file.write(uml_diagram)

        puml = PlantUML(url='http://www.plantuml.com/plantuml/img/')

        puml.processes_file("temp/diagram.puml")

        print("UML диаграмма успешно создана и сохранена как diagram.png")
    except Exception as e:
        print(f"Произошла ошибка при создании UML диаграммы: {e}")


if __name__ == "__main__":
    create_uml_diagram()