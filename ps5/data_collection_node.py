#!/usr/bin/env python3
"""
Pose data collection for occlusion-conditioned noise characterization.

The FoundationPose pose topic is used ONLY as a timer: on each message we take
its stamp and look up all three frames from TF at that time, expressed in the
world frame (fr3_link0):
    fp_T                       -> T object pose  (columns t_*)
    fr3_pusher_tcp              -> end-effector   (columns ee_*)
    camera_color_optical_frame -> camera         (columns cam_*)

No pose data is read from the trigger message itself.

Start/stop over std_srvs/Trigger services.
"""

import argparse
import csv
import os
import threading
from datetime import datetime

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from std_srvs.srv import Trigger
from geometry_msgs.msg import PoseStamped

import tf2_ros
from tf2_ros import TransformException

WORLD_FRAME = "fr3_link0"
OUTPUT_DIR = os.path.expanduser("~/data_collection")


def _cols(prefix):
    return [f"{prefix}_{c}" for c in ("x", "y", "z", "qx", "qy", "qz", "qw")]


class DataCollectionNode(Node):
    def __init__(self, pose_topic, t_frame, ee_frame, cam_frame, tf_timeout,
                 max_stale):
        super().__init__("data_collection_node")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        self._active = False
        self._buffer = []
        self._lock = threading.Lock()
        self._frames = {"t": t_frame, "ee": ee_frame, "cam": cam_frame}
        self._tf_timeout = tf_timeout
        self._max_stale = max_stale
        self._dropped = 0
        self._stale_dropped = 0

        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)

        self.create_subscription(PoseStamped, pose_topic, self._on_tick, 50)
        self.create_service(Trigger, "/data_collection/start", self._start)
        self.create_service(Trigger, "/data_collection/stop", self._stop)

        self.get_logger().info(
            f"Ready (idle). timer={pose_topic} T={t_frame} EE={ee_frame} "
            f"CAM={cam_frame} world={WORLD_FRAME}")

    def _lookup_latest(self, frame):
        """Latest available transform (Time() == 0 == latest). Returns
        (values, tf_stamp_seconds) so the caller can enforce staleness."""
        tf = self._tf_buffer.lookup_transform(
            WORLD_FRAME, frame, Time(),
            timeout=rclpy.duration.Duration(seconds=self._tf_timeout))
        t = tf.transform.translation
        r = tf.transform.rotation
        s = tf.header.stamp
        return ((t.x, t.y, t.z, r.x, r.y, r.z, r.w),
                s.sec + s.nanosec * 1e-9)

    def _on_tick(self, msg):
        if not self._active:
            return
        tick = msg.header.stamp
        tick_s = tick.sec + tick.nanosec * 1e-9
        try:
            vals, tf_stamps = {}, {}
            for label, frame in self._frames.items():
                v, ts = self._lookup_latest(frame)
                vals[label] = v
                tf_stamps[label] = ts
        except TransformException as e:
            self._dropped += 1
            if self._dropped % 30 == 1:
                self.get_logger().warn(f"TF lookup failed ({self._dropped}): {e}")
            return

        # Staleness guard applies ONLY to fp_T (the vision frame that drops
        # out under occlusion). The camera extrinsic is a static/timeless
        # transform and the robot frames are always fresh; their stamps are
        # not comparable to a live wall-clock and must not be checked here.
        # We compare fp_T's stamp against the trigger tick (both live clock).
        t_stamp = tf_stamps["t"]
        t_lag = tick_s - t_stamp
        if t_lag > self._max_stale:
            self._stale_dropped += 1
            if self._stale_dropped % 30 == 1:
                self.get_logger().warn(
                    f"Stale fp_T, dropping ({self._stale_dropped}): "
                    f"lags tick by {t_lag*1e3:.0f} ms")
            return

        row = {"tick_stamp": tick_s}
        for label, v in vals.items():
            for c, val in zip(("x", "y", "z", "qx", "qy", "qz", "qw"), v):
                row[f"{label}_{c}"] = val
            row[f"{label}_tf_stamp"] = tf_stamps[label]
        with self._lock:
            self._buffer.append(row)

    def _start(self, req, resp):
        if self._active:
            resp.success, resp.message = False, "Already collecting"
            return resp
        with self._lock:
            self._buffer = []
        self._dropped = 0
        self._stale_dropped = 0
        self._active = True
        self.get_logger().info("Collection STARTED")
        resp.success, resp.message = True, "started"
        return resp

    def _stop(self, req, resp):
        if not self._active:
            resp.success, resp.message = False, "Not collecting"
            return resp
        self._active = False
        with self._lock:
            rows = list(self._buffer)
            self._buffer = []
        if not rows:
            self.get_logger().warn("Stopped with empty buffer")
            resp.success, resp.message = True, "stopped (no data)"
            return resp

        path = os.path.join(
            OUTPUT_DIR, f"collection_{datetime.now():%Y%m%d_%H%M%S}.csv")
        keys = ["tick_stamp"]
        for label in ("t", "ee", "cam"):
            keys += _cols(label) + [f"{label}_tf_stamp"]
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
        self.get_logger().info(
            f"Wrote {len(rows)} rows "
            f"({self._dropped} TF-fail, {self._stale_dropped} stale) -> {path}")
        resp.success, resp.message = True, path
        return resp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pose-topic", default="/tracking/foundationpose/pose",
                    help="FoundationPose PoseStamped used only as a timer")
    ap.add_argument("--t-frame", default="fp_T", help="T object TF frame")
    ap.add_argument("--ee-frame", default="fr3_pusher_tcp", help="end-effector TF frame")
    ap.add_argument("--cam-frame", default="camera_color_optical_frame",
                    help="camera optical TF frame")
    ap.add_argument("--tf-timeout", type=float, default=0.05,
                    help="TF lookup timeout, seconds")
    ap.add_argument("--max-stale", type=float, default=0.15,
                    help="drop row if any frame's TF lags the newest by more "
                         "than this (s); catches FoundationPose dropout")
    args, _ = ap.parse_known_args()

    rclpy.init()
    node = DataCollectionNode(
        args.pose_topic, args.t_frame, args.ee_frame, args.cam_frame,
        args.tf_timeout, args.max_stale)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
