import pygame

from symaX400 import SymaX400

if __name__ == '__main__':
    pygame.init()
    screen = pygame.display.set_mode([500, 500])

    x400 = SymaX400(
        # init with some trim [-15, 15] to save time adjusting on each flight
        init_pitch_trim_pos=-3,
        init_roll_trim_pos=-2)
    # Mapping keyboard inputs to the flight controls
    drone_control_map = {
        # pitch forward
        pygame.K_UP: lambda is_pressed: x400.set_pitch(1 * scale if is_pressed else 0),
        # pitch backward
        pygame.K_DOWN: lambda is_pressed: x400.set_pitch(-1 * scale if is_pressed else 0),
        # roll right
        pygame.K_RIGHT: lambda is_pressed: x400.set_roll(1 * scale if is_pressed else 0),
        # roll left
        pygame.K_LEFT: lambda is_pressed: x400.set_roll(-1 * scale if is_pressed else 0),
        # yaw right
        pygame.K_d: lambda is_pressed: x400.set_yaw(1 * scale if is_pressed else 0),
        # yaw left
        pygame.K_a: lambda is_pressed: x400.set_yaw(-1 * scale if is_pressed else 0),
        # throttle up
        pygame.K_w: lambda is_pressed: x400.set_throttle(1 * scale if is_pressed else 0),
        # throttle down
        pygame.K_s: lambda is_pressed: x400.set_throttle(-1 * scale if is_pressed else 0),
        # connect to the drone
        pygame.K_SPACE: lambda is_pressed: x400.connect() if is_pressed else None,
        # turn the motors on
        pygame.K_RETURN: lambda is_pressed: x400.toggle_motor_power() if is_pressed else None,
        # take off into the air!
        pygame.K_t: lambda is_pressed: x400.auto_land() if is_pressed else None,
        # land on the ground
        pygame.K_g: lambda is_pressed: x400.auto_take_off() if is_pressed else None,
        # stream video
        pygame.K_v: lambda is_pressed: x400.video_stream() if is_pressed else None,
    }

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYUP or event.type == pygame.KEYDOWN:
                if event.key in drone_control_map:
                    drone_control_map[event.key](event.type == pygame.KEYDOWN)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_0:
                        scale = 1
                    elif event.key == pygame.K_1:
                        scale = .1
                    elif event.key == pygame.K_2:
                        scale = .2
                    elif event.key == pygame.K_3:
                        scale = .3
                    elif event.key == pygame.K_4:
                        scale = .4
                    elif event.key == pygame.K_5:
                        scale = .5
                    elif event.key == pygame.K_6:
                        scale = .6
                    elif event.key == pygame.K_7:
                        scale = .7
                    elif event.key == pygame.K_8:
                        scale = .8
                    elif event.key == pygame.K_9:
                        scale = .9
    x400.connect(False)
    pygame.quit()
