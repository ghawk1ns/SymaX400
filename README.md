
# How to Control


See `example.py` to fly the x400 with your keyboard
```commandline
# Create an X400 Instance
x400 = SymaX400()

# Connect to the drone and start listening for control inputs
x400.connect()

# Optional: Start the video stream
# x400.video_stream()

# Turn the motors on
x400.toggle_motor_power()

# Bring the drone up
x400.auto_take_off()

# Adjust the trim
x400.pitch_trim_forward()
x400.pitch_trim_backward()
x400.roll_trim_left()
x400.roll_trim_right()


# Pitch forward/backwards using the float range [-1.0, 1.0]
x400.set_pitch(.75)
time.sleep(1)
x400.set_pitch(0)


# Roll left/right using the float range [-1.0, 1.0]
x400.set_roll(.75)
time.sleep(1)
x400.set_roll(0)

# Throttle up/down using the float range [-1.0, 1.0]
x400.set_throttle(1)
time.sleep(.75)
x400.set_throttle(0)

# Yaw left/right using the float range [-1.0, 1.0]
x400.set_yaw(.75)
time.sleep(1)
x400.set_yaw(0)


# land the drone
x400.auto_land()

# Disconnect, stop the video and command streams
x400.connect(False)        
```


# The Drone Command
| byte | default | description                                                                                                                             |
|------|---------|-----------------------------------------------------------------------------------------------------------------------------------------|
| 0    | 0xA5    | hard-coded header value                                                                                                                 |
| 1    | 0xA5    | hard-coded header value                                                                                                                 |
| 2    | 0x0C    | number of remaining bytes (12) (hard-coded)                                                                                             |
| 3    | 0x80    | Throttle                                                                                                                                |
| 4    | 0x80    | Pitch                                                                                                                                   |
| 5    | 0x80    | Yaw                                                                                                                                     |
| 6    | 0x80    | Roll                                                                                                                                    |
| 7    | 0x20    | ???                                                                                                                                     |
| 8    | 0x20    | Pitch Trim                                                                                                                              |
| 9    | 0x20    | ???                                                                                                                                     |
| 10   | 0x20    | Roll Trim                                                                                                                               |
| 11   | 0x00    | Drone Actions (e.g. auto takeoff/land)                                                                                                  |
| 12   | 0x55    | flight commands checksum (((((cmd[7], ^ ((cmd[5], ^ (cmd[4], ^ cmd[3],)) ^ cmd[6],)) ^ cmd[8],) ^ cmd[9],) ^ cmd[10],) ^ cmd[11],) + 85 |
| 13   | 0xe0    | checksum lower byte                                                                                                                     |
| 14   | 0x03    | checksum upper byte                                                                                                                     |


The default heart-beat command. Keeps the connection with drone open but does not apply any directional power to the axis
```
[0xA5, 0x5A, 0x0C, 0x80, 0x80, 0x80, 0x20, 0x20, 0x20, 0x20, 0x00, 0x55, 0xE0, 0x03]
```
Start the motors - rotates the blades at a low RPM, not enough for list
```
[0xA5, 0x5A, 0x0C, 0x80, 0x80, 0x80, 0x20, 0x20, 0x20, 0x20, 0x10, 0x65, 0x00, 0x04]
```
Auto-Land - Brings the drone back to the ground and cuts the motors off
```
[0xA5, 0x5A, 0x0C, 0x80, 0x80, 0x80, 0x20, 0x20, 0x20, 0x20, 0x08, 0x5D, 0xF0, 0x03]
```
Auto-Lift - Brings the drone up a few feet and hovers
```
[0xA5, 0x5A, 0x0C, 0x80, 0x80, 0x80, 0x20, 0x20, 0x20, 0x20, 0x60, 0x09, 0x56, 0x00]
```
Calibrate - I don't actually know what this does
```
[0xA5, 0x5A, 0x0C, 0x80, 0x80, 0x80, 0x20, 0x20, 0x20, 0x20, 0x20, 0x75, 0x20, 0x04]
```


### Axis Values


`0x80` is the neutral value for each axis

| Axis     | Direction | [Low, High]  |
|----------|-----------|--------------|
| Throttle | N/A       | [0x00, 0xFF] |
| Pitch    | Forward   | [0x00, 0x7F] |
| Pitch    | Backward  | [0x81, 0xFF] |
| Roll     | Left      | [0x00, 0x7F] |
| Roll     | Right     | [0x81, 0xFF] |
| Yaw      | Left      | [0x00, 0x7F] |
| Yaw      | Right     | [0x81, 0xFF] |

### Trim Values

`0x20` is the neutral value for each trim  

| Trim  | Direction | [Low, High]  |
|-------|-----------|--------------|
| Pitch | Forward   | [0x00, 0x0F] |
| Pitch | Backward  | [0x21, 0x2F] |
| Roll  | Left      | [0x00, 0x0F] |
| Roll  | Right     | [0x21, 0x2F] |

# Misc


Waiting on the UX to scan / display the drone wifi is annoying, connect quicker in the terminal. replace `FPV_WIFI__8B06` with your drone's wifi name

Mac
```
networksetup -setairportnetwork en0 "FPV_WIFI__8B06"
```
Linux
```
nmcli device wifi connect FPV_WIFI__8B06
```