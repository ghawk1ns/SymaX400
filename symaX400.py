import operator
import threading
import socket
import time
import logging
import queue
from functools import reduce

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class SymaX400:
    # Drone Network
    _DRONE_IP = "192.168.29.1"
    _DRONE_CMD_PORT = 25000
    _VID_CMD_PORT = 20000
    _VID_IN_PORT = 10900

    # Video Commands
    _VID_INIT_A_CMD = b"JHCMD\x10\x00"
    _VID_INIT_B_CMD = b"JHCMD\x20\x00"
    _VID_STOP_CMD = b"JHCMD\xd0\x02"
    _VID_HB_CMD = b"JHCMD\xd0\x01"

    _DRONE_CMD_HEADER = [0xA5, 0x5A, 0x0C]
    # Drone Action Commands
    _DRONE_IDLE_CMD = bytes.fromhex("a55a0c80808080202020200055e003")
    _DRONE_TOGGLE_MOTOR_CMD = bytes.fromhex('a55a0c808080802020202010650004')
    _DRONE_AUTO_LAND = bytes.fromhex("a55a0c8080808020202020085df003")
    _DRONE_AUTO_LIFT = bytes.fromhex("a55a0c808080802020206000956004")
    _DRONE_CALIBRATE_CMD = bytes.fromhex("a55a0c808080802020202020752004")

    # TODO: Investigate high rotate speed and high speed commands (and calc checksum)
    # high_rotation_speed  = bytes.fromhex("a55a0c 8080808020a0202000d5XXXX")
    # DRONE_HIGH_SPEED_CMD = bytes.fromhex("a55a0c808080802020a0a00055XXXX")

    def __init__(self, video_port=10901, init_pitch_trim_pos=0, init_roll_trim_pos=0):
        self.video_out_port = video_port
        self.cmd_thread = None
        self.video_stream_thread = None
        # true if the controller should connect to the drone
        self.should_connect_to_drone = False
        # true if the drone should stream video
        self.should_stream_video = False
        self.action_cmd_queue = queue.Queue()
        # Create a logger
        self.logger = logging.getLogger("x400")

        # Flight Controls 

        # defaults
        self._axis_neutral_val = 0x80
        self._input_max = 1
        self._input_min = -1

        self._trim_neutral_val = 0x20
        self._trim_left_min = 0x01
        self._trim_right_min = 0x21

        # Axis stuff
        self._pitch = self._roll = self._yaw = self._throttle = self._yaw_trim = self._axis_neutral_val

        # Trim Stuff
        self._trim_boundary = 15
        self._pitch_trim_pos = self._clamp_trim_pos(init_pitch_trim_pos)
        self._roll_trim_pos = self._clamp_trim_pos(init_roll_trim_pos)
        # TODO: Trim for yaw/pitch?
        # 0x20 is neutral trim
        # one side of trim starts at 0x1, the other side of trim starts at 0x21
        # each trim gets stronger as you increase from there
        self._trim_map = {0: 0x20}
        # build a map for the range [(-trim_boundary, 0x0f), ..., (-1, _trim_left_min), (0, _trim_neutral_val), (1, _trim_right_min), ..., (trim_boundary, 0x2f)]
        for x in range(0, self._trim_boundary):
            idx = x + 1
            self._trim_map[-idx] = self._trim_left_min + x
            self._trim_map[idx] = self._trim_right_min + x

    def idle_controls(self):
        """
        Reset all Axis values back to the neutral position
        """
        self._throttle = self._axis_neutral_val  # Vertical speed (up/down)
        self._pitch = self._axis_neutral_val  # Forward/Backward tilt
        self._roll = self._axis_neutral_val  # Left/Right tilt
        self._yaw = self._axis_neutral_val  # Rotation around vertical axis

    def neutral_trim(self):
        """
        Reset the trim position back to neutral 
        """
        self._pitch_trim_pos = 0
        self._roll_trim_pos = 0

    def set_throttle(self, value):
        self._throttle = 0x80 if value == 0 else int((self._clamp_axis_input(value) + 1) * 0xff / 2)
        # self._throttle = self._sanitize_axis_input_val(value)

    def set_pitch(self, value):
        self._pitch = self._sanitize_axis_input_val(value)

    def set_yaw(self, value):
        self._yaw = self._sanitize_axis_input_val(value)

    def set_roll(self, value):
        self._roll = self._sanitize_axis_input_val(value)

    def pitch_trim_forward(self):
        """
        forward: 01++
        neutral: 20
        backward: 21++
        """
        self._pitch_trim_pos = self._clamp_trim_pos(self._pitch_trim_pos - 1)
        self.logger.debug(f"_pitch_trim_pos: {self._pitch_trim_pos}")

    def pitch_trim_backward(self):
        """
        forward: 01++
        neutral: 20
        backward: 21++
        """
        self._pitch_trim_pos = self._clamp_trim_pos(self._pitch_trim_pos + 1)
        self.logger.debug(f"_pitch_trim_pos: {self._pitch_trim_pos}")

    def roll_trim_left(self):
        """
        left: 01++
        neutral: 20
        right: 21++
        """
        self._roll_trim_pos = self._clamp_trim_pos(self._roll_trim_pos - 1)
        self.logger.debug(f"_roll_trim_pos: {self._pitch_trim_pos}")

    def roll_trim_right(self):
        """
        left: 01++
        neutral: 20
        right: 21++
        """
        self._roll_trim_pos = self._clamp_trim_pos(self._roll_trim_pos + 1)
        self.logger.debug(f"_roll_trim_pos: {self._pitch_trim_pos}")

    def toggle_motor_power(self):
        self.logger.debug("toggle_motor_power")
        self.action_cmd_queue.put(self._DRONE_TOGGLE_MOTOR_CMD)

    def auto_take_off(self):
        self.logger.debug("auto_take_off")
        self.action_cmd_queue.put(self._DRONE_AUTO_LIFT)

    def auto_land(self):
        self.logger.debug("auto_land")
        self.action_cmd_queue.put(self._DRONE_AUTO_LAND)

    def auto_calibrate(self):
        self.logger.debug("auto_calibrate")
        self.action_cmd_queue.put(self._DRONE_CALIBRATE_CMD)

    def _clamp_axis_input(self, value):
        """
        :param value: axis input value
        :return: Clamped position to the range [-_input_min, _input_max]
        """
        return max(self._input_min, min(value, self._input_max))

    def _clamp_trim_pos(self, trim_pos):
        """
        :param trim_pos: a position in trim
        :return: Clamped position to the range [-trim_boundary, trim_boundary]
        """
        return max(-self._trim_boundary, min(trim_pos, self._trim_boundary))

    def _linear_interpolation(self, axis_input, cmd_low, cmd_high):
        """
        :param axis_input: axis input in the float range [-1, 0]
        :param cmd_low: the axis cmd's high value
        :param cmd_high: the axis cmd's low value
        :return: the axis cmd value mapped from the axis input value
        """
        return cmd_low + (abs(axis_input) * (cmd_high - cmd_low) / 1)

    def _sanitize_axis_input_val(self, input_val):
        """
        :param input_val: the input value for the control
        :param ctl_min: the lowest value the control can be
        :param ctl_max: the largest value the control can be
        :return: the input val sanitized and mapped to a control value
        """
        input_val = self._clamp_axis_input(input_val)
        if input_val > 0:
            return int(self._linear_interpolation(input_val, self._axis_neutral_val + 1, 0xFF))
        elif input_val < 0:
            return int(self._linear_interpolation(input_val, 0x01, self._axis_neutral_val - 1))
        else:
            return self._axis_neutral_val

    def _get_flight_cmd(self):
        """
        Some things to consider when rev-engineering the cmds from the syma_fly android app
        In java land, byte is a signed 8-bit type, ranging from -128 to 127. Here bytes are unsigned, 0 to 255.
        
        @Return bytes 3-12 of the drone cmd, representing the drone's flight controls
        """
        cmd = [0] * 10
        cmd[0] = self._throttle
        cmd[1] = self._pitch
        cmd[2] = self._yaw
        cmd[3] = self._roll
        cmd[4] = 0x20  # trim???
        cmd[5] = self._trim_map[self._pitch_trim_pos]
        cmd[6] = 0x20  # trim????
        cmd[7] = self._trim_map[self._roll_trim_pos]
        cmd[8] = 0x00  # Drone Actions unused in axis flight control
        # TODO: Deeper dive into why the Syma_fly app checksums this way
        checksum = (reduce(operator.xor, cmd) & 0xFF) + 85
        if checksum > 0xFF:
            checksum -= 0xFF + 1
        cmd[9] = checksum
        return cmd

    def _get_drone_cmd(self):
        """
        :return: the entire drone cmd: header + flight_cmd + checksum  
        """
        cmd = self._DRONE_CMD_HEADER + self._get_flight_cmd()
        checksum = sum(cmd)
        cmd.append(checksum & 0xFF)
        cmd.append((checksum >> 8) & 0xFF)
        self.logger.debug([hex(a) for a in cmd])
        return bytes(cmd)

    def connect(self, should_connect=True):
        self.logger.debug(f"should_connect: {should_connect}")
        self.should_connect_to_drone = should_connect
        if should_connect:
            if self.cmd_thread is None or not self.cmd_thread.is_alive():
                self.cmd_thread = threading.Thread(target=self._runner)
                self.cmd_thread.daemon = True
                self.cmd_thread.start()
        else:
            self.video_stream(False)

    def _runner(self):
        self.logger.debug("Opening Connection to x400")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            while self.should_connect_to_drone:
                # Fire off events from the action queue, otherwise fire a flight_control event
                if not self.action_cmd_queue.empty():
                    action_cmd = self.action_cmd_queue.get()
                    self.logger.debug(f"Dispatch Action: {action_cmd}")
                    # drone action cmds seem to be sent ~15 times
                    for _ in range(15):
                        s.sendto(action_cmd, (self._DRONE_IP, self._DRONE_CMD_PORT))
                else:
                    s.sendto(self._get_drone_cmd(), (self._DRONE_IP, self._DRONE_CMD_PORT))
                time.sleep(0.02)

    def video_stream(self, should_stream_video=True):
        self.logger.debug(f"should_stream_video: {should_stream_video}")
        self.should_stream_video = should_stream_video
        if should_stream_video and (self.video_stream_thread is None or not self.video_stream_thread.is_alive()):
            self.video_stream_thread = threading.Thread(target=self._stream_video)
            self.video_stream_thread.daemon = True
            self.video_stream_thread.start()

    def _stream_video(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as vid_out:
            self.logger.debug("Video Stream init")

            for start_seq_cmd in [self._VID_INIT_A_CMD, self._VID_INIT_B_CMD, self._VID_HB_CMD]:
                for _ in range(3):
                    vid_out.sendto(start_seq_cmd, (self._DRONE_IP, self._VID_CMD_PORT))
                    time.sleep(.1)

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as vid_in:
                vid_in.bind(("", self._VID_IN_PORT))
                count = 0
                while self.should_stream_video:
                    try:
                        data = vid_in.recv(1450)
                        vid_out.sendto(data[8:], ("", self.video_out_port))
                    except Exception as e:
                        self.logger.debug(e)
                        time.sleep(0.01)
                    if count > 100:
                        count = 0
                        vid_out.sendto(self._VID_HB_CMD, (self._DRONE_IP, self._VID_CMD_PORT))
                    count += 1
            self.logger.debug("Video Stream stopping")
