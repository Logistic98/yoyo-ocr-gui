# -*- coding: utf-8 -*-

import os
from time import sleep
from PIL import Image, ImageGrab
from ctypes import *


def screenshot(img_path):

    if windll.user32.OpenClipboard(None):
        windll.user32.EmptyClipboard()
        windll.user32.CloseClipboard()

    os.system('start /B rundll32 PrScrn.dll PrScrn')

    # 等待截图后放到剪切板
    index = 0
    im = ImageGrab.grabclipboard()
    while not im:
        if index < 500:
            im = ImageGrab.grabclipboard()
            sleep(0.01)
            index = index + 1
        else:
            break

    if isinstance(im, Image.Image):
        im.save(img_path)

