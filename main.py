# This example demonstrates a peripheral implementing the Nordic UART Service (NUS).
import re
import bluetooth
from ble_advertising import advertising_payload

from micropython import const

from machine import Pin, PWM, Timer
from time import sleep
import machine

# Set up the UART serial connection
py_uart = machine.UART(0, baudrate=115200)
py_uart.init(115200, bits=8, parity=None, stop=1)

# Bluetooth connection
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX = (
    bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"),
    _FLAG_NOTIFY,
)
_UART_RX = (
    bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"),
    _FLAG_WRITE,
)
_UART_SERVICE = (
    _UART_UUID,
    (_UART_TX, _UART_RX),
)

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_COMPUTER = const(128)



number_of_move_intervals = 10
x_move_interval_count = 0
y_move_interval_count = 0
x_move_interval = 0
y_move_interval = 0

#Servo Pins
servoBot = PWM(Pin(32), freq=50)
servoTop = PWM(Pin(14), freq=50)


def map_servo(x, in_min, in_max, out_min, out_max):
    return (int) (x-in_min)*(out_max-out_min)//(in_max - in_min) + out_min

def servo(pin,angle):
    duty = map_servo(angle,0,180,0,100)
    try:
        pin.duty(duty)
    except:
        pass

x_angle_curr_list = [0.0]*10
def runX(timer):
    global x_angle_curr
    global x_angle_curr_list 
    proportional_control = (x_angle_next - x_angle_curr) / number_of_move_intervals
    prop_control_constant = 0.1
    
    movement = x_move_interval + prop_control_constant * proportional_control
    x_angle_curr += movement

    if len(x_angle_curr_list) == 10:
        x_angle_curr_list.pop(0)
    x_angle_curr_list.append(x_angle_curr)       
    servo(servoBot, x_angle_curr)

y_angle_curr_list = [0.0]*10
def runY(timer):
    global y_angle_curr
    global y_angle_curr_list 
    proportional_control = (y_angle_next - y_angle_curr) / number_of_move_intervals
    prop_control_constant = 2
    
    movement = y_move_interval + prop_control_constant * proportional_control
    y_angle_curr += movement
    if len(y_angle_curr_list) == 10:
        y_angle_curr_list.pop(0)
    y_angle_curr_list.append(y_angle_curr)
    servo(servoTop, y_angle_curr)

max_bluetooth_latency = 100


class BLEUART:
    def __init__(self, ble, name="mpy-uart-simon", rxbuf=100):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._tx_handle, self._rx_handle),) = self._ble.gatts_register_services((_UART_SERVICE,))
        # Increase the size of the rx buffer and enable append mode.
        self._ble.gatts_set_buffer(self._rx_handle, rxbuf, True)
        self._connections = set()
        self._rx_buffer = bytearray()
        self._handler = None
        # Optionally add services=[_UART_UUID], but this is likely to make the payload too large.
        self._payload = advertising_payload(name=name, appearance=_ADV_APPEARANCE_GENERIC_COMPUTER)
        self._advertise()

    def irq(self, handler):
        self._handler = handler

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle in self._connections:
                self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection.
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if conn_handle in self._connections and value_handle == self._rx_handle:
                self._rx_buffer += self._ble.gatts_read(self._rx_handle)
                if self._handler:
                    self._handler()

    def any(self):
        return len(self._rx_buffer)

    def read(self, sz=None):
        if not sz:
            sz = len(self._rx_buffer)
        result = self._rx_buffer[0:sz]
        self._rx_buffer = self._rx_buffer[sz:]
        return result

    def write(self, data):
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._tx_handle, data)

    def close(self):
        for conn_handle in self._connections:
            self._ble.gap_disconnect(conn_handle)
        self._connections.clear()

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)

pattern = r"Rect\((-?\d+),\s*(-?\d+)\s*-\s*(-?\d+),\s*(-?\d+)\)"

x_angle_next = 90
y_angle_next = 65

x_angle_curr = x_angle_next
y_angle_curr = y_angle_next

center_x = const(240)
center_y = const(320)

x_conversion_factor = const(0.121)
y_conversion_factor = const(0.07)

# Define hardware timers
t1 = Timer(1)
t2 = Timer(2)

def demo():
    import time
    
    ble = bluetooth.BLE()
    uart = BLEUART(ble)
    
    def on_rx():
        # interrupt
        t1.deinit()
        t2.deinit()
        global x_angle_curr
        global y_angle_curr
        
        global py_uart
        global x_angle_next
        global y_angle_next
        
        global x_move_interval
        global y_move_inteval
        global x_move_interval_count
        global y_move_interval_count
        
        x_move_interval_count = 0
        y_move_interval_count = 0
        
        # ex) Rect(46, 318 - 367, 700)
        rect_raw = uart.read().decode().strip()
        # print("rx: ", rect_raw)
        
        # Regular expression to match the integers
        pattern = r"Rect\((-?\d+),\s*(-?\d+)\s*-\s*(-?\d+),\s*(-?\d+)\)"

        # Extract the integers using the regular expression
        match_new = re.match(pattern, rect_raw)

        # Save the integers in x1, y1, x2, y2
        x1 = int(match_new.group(1))
        y1 = int(match_new.group(2))
        x2 = int(match_new.group(3))
        y2 = int(match_new.group(4))
        
        # logic for getting x1 x2 y1 and y2    
        box_x = (x1 + x2) >> 1
        box_y = (y1 + y2) >> 1
        
        difference_x = (center_x - box_x) * x_conversion_factor
        difference_y = (center_y - box_y) * y_conversion_factor
        
        abs_diff_x = abs(difference_x)
        abs_diff_y = abs(difference_y)
        
        # fine tuning of servo to not overshoot
        if (abs_diff_x < 5):
            difference_x = 0
        elif (abs_diff_x < 7):
            difference_x -=  5 * abs_diff_x / difference_x
        elif (abs_diff_x >= 7):
            difference_x = 2 * abs_diff_x / difference_x
            
        if (abs_diff_y  < 5):
            difference_y = 0
        elif (abs_diff_y < 7):
            difference_y -=  5 * abs_diff_y / difference_y
        elif (abs_diff_y >= 7):
            difference_y = 2 * abs_diff_y / difference_y
        
        
        if (x_angle_next >= 180):
            x_angle_next = 180
            if (difference_x > 0):
                difference_x = 0
        elif (x_angle_next <= 0):
            x_angle_next = 0
            if (difference_x < 0):
                difference_x = 0
            
        if (y_angle_next >= 90):
            y_angle_next = 90
            if (difference_y > 0):
                difference_y = 0
        elif (y_angle_next <= 0):
            y_angle_next = 0
            if (difference_y < 0):
                difference_y = 0
        
        # target angle
        x_angle_next += difference_x
        y_angle_next += difference_y
        
        # send the current state and target state to GUI
        target_gui = '1,'+ str(x_angle_next) + ',' + str(y_angle_next)
        print(target_data)
        
        current_gui = '0'
        for i in range(5):
            current_gui = current_gui +','+ str(x_angle_curr_list[i]) + ',' + str(y_angle_curr_list[i])
        print(current_gui)
        
        x_move_interval = difference_x / number_of_move_intervals
        y_move_interval = difference_y / number_of_move_intervals
        
        # start hardware timers for servo movement
        t1.init(period=max_bluetooth_latency // number_of_move_intervals, mode=t1.PERIODIC, callback=runX)
        t2.init(period=max_bluetooth_latency // number_of_move_intervals, mode=t1.PERIODIC, callback=runY)
        
    uart.irq(handler=on_rx)
    try:
        while True:           
            time.sleep_ms(1000)
    except KeyboardInterrupt:
        pass

    #uart.close()

if __name__ == "__main__":    
    servo(servoBot, 90)
    servo(servoTop, 65)
    demo()





