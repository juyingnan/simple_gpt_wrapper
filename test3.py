import sys
import json
from PyQt5.QtWidgets import QWidget, QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, \
    QSplitter, QComboBox, QLabel, QSlider, QFrame, QLineEdit
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt, pyqtSignal

# Note: The openai-python library support for Azure OpenAI is in preview.
# import os
import openai


def read_config_file(config_file_path):
    with open(config_file_path, 'r') as f:
        return json.load(f)


config_data = read_config_file('config.json')
openai.api_type = config_data['api_type']
openai.api_base = config_data['endpoint']
openai.api_version = config_data['api_version']
openai.api_key = config_data['api_key']
openai_key = config_data['openai_key']
default_model = config_data['default_model']
default_callback_num = config_data['default_callback_num']
model_names = config_data['model_names']
default_temperature = config_data['temperature']

user_input_color = QColor(0, 128, 0)  # green
ai_response_color = QColor(0, 0, 255)  # blue
system_message_color = QColor(0, 0, 0)  # black


# defining a function to create the prompt from the system message and the messages
def create_prompt(system_message, messages):
    prompt = system_message
    message_template = "\n<|im_start|>{}\n{}\n<|im_end|>"
    for message in messages:
        prompt += message_template.format(message['sender'], message['text'])
    prompt += "\n<|im_start|>assistant\n"
    return prompt


# build an input text box which uses enter to send / shift+enter to change line
class MyTextEdit(QTextEdit):
    enter_pressed = pyqtSignal()

    def __init__(self):
        super().__init__()

    # noinspection PyUnresolvedReferences
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
            # Emit the enter_pressed signal
            self.enter_pressed.emit()
        else:
            # Allow normal text editing behavior
            super().keyPressEvent(event)


# create the main application window
class MainWindow(QMainWindow):
    # noinspection PyUnresolvedReferences
    def __init__(self):
        super().__init__()
        # initialize the parameters
        self.model = default_model
        self.callback_num = default_callback_num
        self.temperature = default_temperature
        # defining the system message
        self.system_message_template = "<|im_start|>system\n{}\n<|im_end|>"
        self.system_message_content = "You are an AI assistant that helps people find information."
        self.system_message_instance = self.system_message_template.format(self.system_message_content)
        self.prefix_message = ""

        self.setWindowTitle("GPT Chat")
        self.resize(1000, 1000)

        # create the chat display widget
        # font = QFont('Microsoft YaHei', 12)
        font = QFont('Arial', 12)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(font)

        # create the user input widget
        self.user_input = MyTextEdit()
        # self.user_input.setFixedSize(400, 300)
        self.user_input.setFont(font)
        self.user_input.setAcceptRichText(False)
        self.user_input.enter_pressed.connect(self.on_user_input)
        # self.user_input.returnPressed.connect(self.on_user_input)

        # create vertical splitter
        splitter = QSplitter()
        splitter.setOrientation(0)
        splitter.addWidget(self.chat_display)
        splitter.addWidget(self.user_input)
        splitter.setSizes([self.height() * 4 // 5, self.height() // 5])
        # splitter.splitterMoved.connect(self.on_splitter_moved)

        # create the submit button
        self.submit_button = QPushButton("Send")
        self.submit_button.clicked.connect(self.on_user_input)

        # add a separator
        self.separator = QFrame(self)
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)

        # create the clear button
        self.clear_button = QPushButton('Clear history')
        self.clear_button.clicked.connect(self.clear_history)

        # create a dropdown menu for model
        self.comboBox_model = QComboBox(self)
        for model_name in model_names:
            self.comboBox_model.addItem(model_name)
        self.comboBox_model.activated[str].connect(self.on_model_selection_activated)

        # create a label to display the selected model
        self.label_model = QLabel(self)
        self.label_model.setText(f"Selected model:")

        # create a dropdown menu for history length
        self.comboBox_history = QComboBox(self)
        for i in range(11):
            self.comboBox_history.addItem(str(i))
        self.comboBox_history.addItem(str(999))
        self.comboBox_history.setCurrentIndex(self.callback_num)
        self.comboBox_history.activated[str].connect(self.on_history_length_selection_activated)

        # create a label to display the selected model
        self.label_history = QLabel(self)
        self.label_history.setText(f"History length:")

        # create a slider to set temperature from 0.0 to 1.0
        self.label_temperature = QLabel(self)
        self.label_temperature.setText(f"temperature: {self.temperature}")
        self.slider_temperature = QSlider(Qt.Horizontal)
        self.slider_temperature.setRange(0, 100)
        self.slider_temperature.setValue(int(self.temperature * 100))
        self.slider_temperature.setSingleStep(5)
        self.slider_temperature.setPageStep(10)
        self.slider_temperature.valueChanged.connect(self.on_temperature_value_changed)

        # add a separator2
        self.separator2 = QFrame(self)
        self.separator2.setFrameShape(QFrame.HLine)
        self.separator2.setFrameShadow(QFrame.Sunken)

        # add a system message box and button
        self.label_system_message = QLabel("System Message:", self)
        self.textbox_system_message = QLineEdit(self.system_message_content, self)
        self.button_update_system_message = QPushButton('Update', self)
        self.button_update_system_message.clicked.connect(self.update_system_message)

        # add a prefix message box and button
        self.label_prefix_message = QLabel("Prefix Message:", self)
        self.textbox_prefix_message = QLineEdit(self)
        self.button_update_prefix_message = QPushButton('Update', self)
        self.button_update_prefix_message.clicked.connect(self.update_prefix_message)

        # create the layout
        # chat and submit button
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        layout.addWidget(self.submit_button)
        layout.addWidget(self.separator)
        # parameter controls
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.label_model)
        input_layout.addWidget(self.comboBox_model)
        input_layout.addWidget(self.label_history)
        input_layout.addWidget(self.comboBox_history)
        input_layout.addWidget(self.label_temperature)
        input_layout.addWidget(self.slider_temperature)
        input_layout.addWidget(self.clear_button)
        # system message
        input_layout2 = QHBoxLayout()
        input_layout2.addWidget(self.label_system_message)
        input_layout2.addWidget(self.textbox_system_message)
        input_layout2.addWidget(self.button_update_system_message)
        # prefix message
        input_layout3 = QHBoxLayout()
        input_layout3.addWidget(self.label_prefix_message)
        input_layout3.addWidget(self.textbox_prefix_message)
        input_layout3.addWidget(self.button_update_prefix_message)
        # all layouts
        layout.addLayout(input_layout)
        layout.addWidget(self.separator2)
        layout.addLayout(input_layout2)
        layout.addLayout(input_layout3)

        # create the widget to hold the layout
        widget = QWidget()
        widget.setLayout(layout)

        # set the main window widget
        self.setCentralWidget(widget)

        # initialize the messages list
        self.messages = []

    # dropdown menu activated function - model selection
    def on_model_selection_activated(self, text):
        # call the selected GPT model based on the user's selection
        self.model = text
        # self.label_model.setText(f"Selected model: {text}")
        self.chat_display.setTextColor(system_message_color)
        self.chat_display.append(f"Current model changed to: {text}")

    # dropdown menu activated function - model selection
    def on_history_length_selection_activated(self, text):
        # call the selected GPT model based on the user's selection
        self.callback_num = int(text)
        # self.label_model.setText(f"Selected model: {text}")
        self.chat_display.setTextColor(system_message_color)
        self.chat_display.append(f"Current history changed to: {text}")
        # trim message list on limit changed
        self.trim_message_list(self.callback_num * 2)
        print("message length: ", len(self.messages), "\thistory: ", self.callback_num)

    def on_temperature_value_changed(self, value):
        self.temperature = float(value) / 100
        self.label_temperature.setText(f"temperature: {self.temperature:.2f}")
        # self.chat_display.append(f"Current temperature changed to: {self.temperature}")

    def clear_history(self):
        self.messages = []
        self.chat_display.clear()
        self.chat_display.setTextColor(system_message_color)
        self.chat_display.append(f"Chat history cleared. You can begin a new chat session.")

    def update_system_message(self):
        self.system_message_content = self.textbox_system_message.text()
        self.system_message_instance = self.system_message_template.format(self.system_message_content)
        self.chat_display.append(f'System message updated to: \n"{self.system_message_content}"')

    def update_prefix_message(self):
        self.prefix_message = self.textbox_prefix_message.text()
        self.chat_display.append(f'Prefix message updated to: \n"{self.prefix_message}"')

    def trim_message_list(self, trim_limit):
        if len(self.messages) > trim_limit:
            # if history = 0, empty the message
            # if history > 0, keep callback_num * 2 messages (human + AI)
            self.messages = self.messages[-trim_limit:] if self.callback_num > 0 else []

    # function to handle user input
    def on_user_input(self):
        # get the user input
        user_input = self.user_input.toPlainText()
        if len(self.prefix_message.strip()) > 0:
            user_input = self.prefix_message + '\n' + user_input

        # clear the user input widget
        self.user_input.setText("")
        # update the chat display widget
        self.chat_display.setTextColor(user_input_color)
        self.chat_display.append("You: " + user_input)
        # self.chat_display.setTextColor(system_message_color)

        # add the user message to the messages list
        self.messages.append({"sender": "user", "text": user_input})
        print(user_input)

        # generate the AI response
        response = openai.Completion.create(
            engine=self.model,
            prompt=create_prompt(self.system_message_instance, self.messages),
            temperature=self.temperature,
            max_tokens=1000,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=["<|im_end|>"])

        ai_response = response.choices[0].text.strip()
        print(ai_response)

        # add the AI response to the messages list
        self.messages.append({"sender": "assistant", "text": ai_response})
        print(self.messages)
        self.trim_message_list(self.callback_num * 2)
        print("message length: ", len(self.messages), "\thistory: ", self.callback_num)

        # update the chat display widget
        self.chat_display.setTextColor(ai_response_color)
        self.chat_display.append("AI: " + ai_response)

        self.chat_display.setTextColor(system_message_color)
        self.chat_display.append("\n--------\n")


# create the application
app = QApplication(sys.argv)

# create the main window
window = MainWindow()

# show the main window
window.show()

# run the application
sys.exit(app.exec_())
