import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import TwistStamped

# --- fill these in ---
TWIST_TOPIC = "/servo_node/delta_twist_cmds"
JOY_TOPIC = "/joy"
FRAME_ID = "base"
PUBLISH_RATE = 100.0
ENABLE_BUTTON = 4              # deadman (e.g. L1); set to None to disable

# axis indices — VERIFY with `ros2 topic echo /joy`
AXIS_LEFT_X = 0               # left stick horizontal
AXIS_LEFT_Y = 1               # left stick vertical
AXIS_R2 = 5                   # right trigger -> speed

DEADZONE = 0.05               # applied to stick magnitude
MAX_LINEAR = 1.0              # keep in [-1,1] if Servo command_in_type == "unitless"


class JoyToTwist(Node):
    def __init__(self):
        super().__init__("joy_to_twist")
        self._joy = None
        self.create_subscription(Joy, JOY_TOPIC, self._on_joy, 10)
        self.pub = self.create_publisher(TwistStamped, TWIST_TOPIC, 10)
        self.create_timer(1.0 / PUBLISH_RATE, self._on_timer)

    def _on_joy(self, msg):
        self._joy = msg

    def _on_timer(self):
        joy = self._joy
        if joy is None:
            return
        if ENABLE_BUTTON is not None and (
            ENABLE_BUTTON >= len(joy.buttons) or not joy.buttons[ENABLE_BUTTON]
        ):
            return

        sx = joy.axes[AXIS_LEFT_Y]
        sy = joy.axes[AXIS_LEFT_X]
        norm = math.hypot(sx, sy)

        ts = TwistStamped()
        ts.header.stamp = self.get_clock().now().to_msg()
        ts.header.frame_id = FRAME_ID
        ts.twist.linear.z = 0.0

        if norm > DEADZONE:
            # R2 raw [-1,1] resting at -1 -> [0,1]
            mag = max(0.0, min(1.0, (1.0 - joy.axes[AXIS_R2]) / 2.0)) / 10
            dx, dy = sx / norm, sy / norm          # unit direction
            ts.twist.linear.x = MAX_LINEAR * mag * dx
            ts.twist.linear.y = MAX_LINEAR * mag * dy
        else:
            ts.twist.linear.x = 0.0
            ts.twist.linear.y = 0.0

        self.pub.publish(ts)


def main():
    rclpy.init()
    node = JoyToTwist()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
