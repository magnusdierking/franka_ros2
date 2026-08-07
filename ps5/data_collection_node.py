import csv
import os
import threading
from datetime import datetime

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from sensor_msgs.msg import JointState   # placeholder — swap for real msg types

OUTPUT_DIR = os.path.expanduser("~/data_collection")


class DataCollectionNode(Node):
    def __init__(self):
        super().__init__("data_collection_node")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        self._active = False
        self._buffer = []                 # list of row dicts
        self._lock = threading.Lock()

        # --- placeholder subscription: replace with real channels ---
        self.create_subscription(JointState, "/joint_states", self._on_sample, 10)

        self.create_service(Trigger, "/data_collection/start", self._start)
        self.create_service(Trigger, "/data_collection/stop", self._stop)
        self.get_logger().info("Data collection node ready (idle)")

    def _on_sample(self, msg):
        if not self._active:
            return
        # placeholder row schema — depends on real msg type
        row = {"stamp": self._now()}
        for name, pos in zip(msg.name, msg.position):
            row[name] = pos
        with self._lock:
            self._buffer.append(row)

    def _start(self, req, resp):
        if self._active:
            resp.success = False
            resp.message = "Already collecting"
            return resp
        with self._lock:
            self._buffer = []
        self._active = True
        self.get_logger().info("Collection STARTED")
        resp.success = True
        resp.message = "started"
        return resp

    def _stop(self, req, resp):
        if not self._active:
            resp.success = False
            resp.message = "Not collecting"
            return resp
        self._active = False
        with self._lock:
            rows = list(self._buffer)
            self._buffer = []

        if not rows:
            resp.success = True
            resp.message = "stopped (no data)"
            self.get_logger().warn("Stopped with empty buffer")
            return resp

        path = os.path.join(
            OUTPUT_DIR, f"collection_{datetime.now():%Y%m%d_%H%M%S}.csv")
        # union of keys across rows, stamp first
        keys = ["stamp"] + sorted({k for r in rows for k in r if k != "stamp"})
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)

        self.get_logger().info(f"Wrote {len(rows)} rows -> {path}")
        resp.success = True
        resp.message = path
        return resp

    def _now(self):
        t = self.get_clock().now().to_msg()
        return t.sec + t.nanosec * 1e-9


def main():
    rclpy.init()
    node = DataCollectionNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
