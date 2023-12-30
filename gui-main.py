# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import matplotlib.pyplot as plt
import serial
import time
import random

from matplotlib.animation import FuncAnimation
from numpy import double

connected = False
ser = None


def main():
    # Set up the serial connection
    global connected
    global ser
    while not connected:
        try:
            ser = serial.Serial('COM4', 115200)
            ser.flushInput()
            print('Connected to serial port')
            connected = True
        except serial.SerialException:
            print('Failed to connect to serial port. Retrying in 1 second...')
            time.sleep(1)

    def read_from_esp32():
        esp32_data = None
        try:
            esp32_data = ser.readline().decode('utf-8').rstrip()
        except KeyboardInterrupt:
            print('User interrupted')
            # Close the serial connection
            ser.close()
        except IOError:
            print('Error occurred')
            # Close the serial connection
            ser.close()
        return esp32_data

    t_x_vals = [0.0] * 5
    t_y_vals = [0.0] * 5
    c_x_vals = [0.0] * 25
    c_y_vals = [0.0] * 25

    plt.style.use('fivethirtyeight')
    

    def animate(i):
        esp = read_from_esp32()
        if (esp == None):
            return
        nums = esp.split(',')
        # print(nums)
        if nums[0] == '1':
            # print(nums)
            tc, x1, y1 = [float(num) for num in nums]
            t_x_vals.pop(0)
            t_x_vals.append(x1)
            t_y_vals.pop(0)
            t_y_vals.append(y1)
            # to avoid the following issue we will clear the axis before plotting
            plt.cla()
            # this method is plotting a brand new line everytime
            # multiple lines are being stacked on top of it
            plt.xlim(0, 180)
            plt.ylim(30, 150)

            target = 'Target'
            plt.plot(t_x_vals, t_y_vals, 'bo', label=target)
            current = 'Current'
            plt.plot(c_x_vals, c_y_vals, 'ro', label=current)
            plt.legend(loc='upper left')

        if nums[0] == '0':
            # print(nums)
            current_list = [float(num) for num in nums]
            current_list.pop(0)
            for i in range(len(current_list)):
                if i % 2 == 1:
                    c_y_vals.pop(0)
                    c_y_vals.append(current_list[i])
                else:
                    c_x_vals.pop(0)
                    c_x_vals.append(current_list[i])

            # to avoid the following issue we will clear the axis before plotting
            plt.cla()
            # this method is plotting a brand new line everytime
            # multiple lines are being stacked on top of it
            plt.xlim(0, 180)
            plt.ylim(30, 150)

            target = 'Target'
            plt.plot(t_x_vals, t_y_vals, 'bo', label=target)
            current = 'Current'
            plt.plot(c_x_vals, c_y_vals, 'ro', label=current)
            plt.legend(loc='upper left')
        # plt.tight_layout()

    # 100ms
    ani = FuncAnimation(plt.gcf(), animate, interval=100)
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()
