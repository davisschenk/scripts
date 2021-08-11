import subprocess
import getch
import threading
import time


BASE_COMMAND = ["adb", "shell", "input", "touchscreen", "swipe"]
DEVICE_WIDTH = 1440
DEVICE_HEIGHT = 2960
BALL_Y = 2630
THROW_FLAG = False


class KeyboardThread(threading.Thread):
    def __init__(self, input_cbk=None, name='keyboard-input-thread'):
        self.input_cbk = input_cbk
        self.data = ""
        self.running = True

        super(KeyboardThread, self).__init__(name=name)
        self.start()

    def run(self):
        while self.running:
            self.data = input("Power 0..100 > ")

    def stop(self):
        self.running = False


def swipe(*args):
    print("Swiping: ", args)
    return subprocess.Popen(BASE_COMMAND + list(map(str, args)))


if __name__ == "__main__":
    kthread = KeyboardThread(lambda s: None)
    proc = swipe(DEVICE_WIDTH / 2, BALL_Y, DEVICE_WIDTH / 2, BALL_Y, 50000)

    try:
        while True:
            print("Main Loop")
            while not kthread.data:
                if proc.poll() is not None:
                    proc.terminate()
                    proc = swipe(DEVICE_WIDTH / 2, BALL_Y, DEVICE_WIDTH / 2, BALL_Y, 50000)

            if kthread.data:
                print("DAta")
                if proc.poll():
                    proc.terminate()

                r = DEVICE_HEIGHT - (DEVICE_HEIGHT - BALL_Y)
                throw_y = (1 - (int(kthread.data) / 100)) * r
                time.sleep(0.2)
                swipe(DEVICE_WIDTH/2, BALL_Y, DEVICE_WIDTH/2, throw_y, 800)
                kthread.data = ""
    except KeyboardInterrupt:
        kthread.stop()
        kthread.join()

