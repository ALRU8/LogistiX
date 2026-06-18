#y = 180 +|^|
#x = 280 +<-
#z = 40 +|^|

import time
from robot_api import ArmController

# Цель 1
target_x = -140
target_y = 120

tolerance = 0.1


controller = ArmController()
controller.connect("COM10", 115200)
controller.rst_xyz()

controller.y_move_pos(120, 150)
controller.x_move_pos(-140, 800)

while True:
    controller.position_timer()
    current_x = controller.wp_axe_x
    current_y = controller.wp_axe_y
    print(current_x, " ", current_y)

    if (abs(current_x - target_x) < tolerance and
        abs(current_y - target_y) < tolerance):
        break

    time.sleep(0.1)

print('OK')

controller.z_move_pos(-20, 800)
controller.x_move_pos(140, 800)

controller.disconnect()