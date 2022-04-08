# -*- coding: utf-8 -*-

import base64
import json
import logging
import os
import sys
import uuid

from configparser import ConfigParser
import qdarkstyle
import requests
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget

import gol
from Ui_YoyoOCR import Ui_YoyoOCR
from PrScrn import screenshot

logging.basicConfig(filename='logging_yoyo_ocr.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 读取配置文件
def read_config():
    cfg = ConfigParser()
    cfg.read('./config.ini', encoding='utf-8')
    paddleocr_url = cfg.get('PaddleOCR', 'url')
    google_translate_url = cfg.get('GoogleTranslate', 'url')
    image_temp_dir = cfg.get('ImageTempDir', 'tmpDir')
    config_dict = {}
    config_dict['paddleocr_url'] = paddleocr_url
    config_dict['google_translate_url'] = google_translate_url
    config_dict['image_temp_dir'] = image_temp_dir
    return config_dict


# 请求GoogleTranslateCrack接口
def google_translate_crack(url, text, to_lang):
    # 传输的数据格式
    data = {'text': text, 'to_lang': to_lang}
    # post传递数据
    r = requests.post(url, data=json.dumps(data))
    # 返回结果
    if json.loads(r.text)['code'] == 200:
        return json.loads(r.text)['data']['result']
    else:
        error_text = "请求Google翻译接口失败！"
        logging.error(error_text)
        return error_text


# 请求PaddleOCR接口
def paddle_ocr(url, imgPath):
    # 测试请求
    f = open(imgPath, 'rb')
    # base64编码
    base64_data = base64.b64encode(f.read())
    f.close()
    base64_data = base64_data.decode()
    # 传输的数据格式
    data = {'img': base64_data}
    # post传递数据
    r = requests.post(url, data=json.dumps(data))
    # 删除临时图片文件
    os.remove(imgPath)
    # 返回结果
    if json.loads(r.text)['code'] == 200:
        content_list = json.loads(r.text)['result']
        result = "\n".join(str(i) for i in content_list)
        return result
    else:
        error_text = "请求PaddleOCR接口失败！"
        logging.error(error_text)
        return error_text


# OCR识别的多线程执行
class WorkThreadOcr(QThread):

    # 自定义信号对象。参数str就代表这个信号可以传一个字符串
    ocrSignal = Signal(str)

    # 初始化函数
    def __int__(self):
        super(WorkThreadOcr, self).__init__()

    # 重写线程执行的run函数，触发自定义信号
    def run(self):
        imgPath = gol.get_value('imgPath')
        # 请求OCR识别接口
        result = paddle_ocr(config_dict['paddleocr_url'], imgPath)
        # 通过自定义信号把待显示的字符串传递给槽函数
        self.ocrSignal.emit(result)


# 文本翻译的多线程执行
class WorkThreadTranslate(QThread):

    # 自定义信号对象。参数str就代表这个信号可以传一个字符串
    translateSignal = Signal(str)

    # 初始化函数
    def __int__(self):
        super(WorkThreadTranslate, self).__init__()

    # 重写线程执行的run函数，触发自定义信号
    def run(self):
        inputText = gol.get_value('inputText')
        languageCode = gol.get_value('languageCode')
        # 请求Google翻译接口
        result = google_translate_crack(config_dict['google_translate_url'], inputText, languageCode)
        # 通过自定义信号把待显示的字符串传递给槽函数
        self.translateSignal.emit(result)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_YoyoOCR()
        self.ui.setupUi(self)
        self.langDict = {
            "中文简体": "zh-cn",
            "中文繁体": "zh-tw",
            "英语": "en",
            "日语": "ja",
            "韩语": "ko",
            "德语": "de",
            "法语": "fr",
            "西班牙语": "es",
            "意大利语": "it",
            "俄语": "ru"
        }
        self.setWindowIcon(QIcon('./logo/logo.png'))
        # 将信号与槽函数绑定
        self.ui.pushButton.clicked.connect(self.queryContent)


    def buttonStatusDisplay(self, status):
        self.ui.pushButton.setText(status)
        app.processEvents()


    def ocrDisplay(self, result):
        # 由于自定义信号时自动传递一个字符串参数，所以在这个槽函数中要接受一个参数
        if result != "":
            self.ui.input.setText(result)
            self.buttonStatusDisplay('开始')


    def translateDisplay(self, result):
        # 由于自定义信号时自动传递一个字符串参数，所以在这个槽函数中要接受一个参数
        if result != "":
            self.ui.output.setText(result)
            self.buttonStatusDisplay('开始')


    def getCode(self, lang):
        return self.langDict.get(lang, '英语')


    def queryContent(self):

        ocrRadio = self.ui.ocrRadioButton.isChecked()
        translateRadio = self.ui.translateRadioButton.isChecked()

        if ocrRadio:
            self.ui.input.clear()
            self.ui.output.clear()
            imgPath = str(config_dict['image_temp_dir']) + '/' + str(uuid.uuid1()) + '.jpg'
            screenshot(imgPath)
            if os.path.exists(imgPath):
                gol.set_value('imgPath', imgPath)
                # 多线程处理OCR识别接口请求
                self.ocr_work = WorkThreadOcr()    # 实例化线程对象
                self.ocr_work.start()  # 启动线程
                self.ocr_work.ocrSignal.connect(self.buttonStatusDisplay('处理中'))
                self.ocr_work.ocrSignal.connect(self.ocrDisplay)   # 线程自定义信号连接的槽函数

        if translateRadio:
            self.ui.output.clear()
            languageName = self.ui.languageComboBox.currentText()
            languageCode = self.getCode(languageName)
            inputText = self.ui.input.toPlainText()
            gol.set_value('languageCode', languageCode)
            gol.set_value('inputText', inputText)
            if inputText != "":
                # 多线程处理Google翻译接口请求
                self.translate_work = WorkThreadTranslate()  # 实例化线程对象
                self.translate_work.start()  # 启动线程
                self.translate_work.translateSignal.connect(self.buttonStatusDisplay('处理中'))
                self.translate_work.translateSignal.connect(self.translateDisplay)  # 线程自定义信号连接的槽函数


if __name__ == '__main__':
    # 读取配置文件
    config_dict = read_config()
    if not os.path.exists(config_dict['image_temp_dir']):
        os.makedirs(config_dict['image_temp_dir'])
    # 全局变量初始化
    gol._init()
    # 初始化界面
    app = QApplication(sys.argv)
    window = MainWindow()
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside6'))
    window.show()
    sys.exit(app.exec())