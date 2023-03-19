import sys
import json
from PyQt5.QtWidgets import QWidget, QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, \
    QSplitter, QComboBox, QLabel
from PyQt5.QtGui import QColor, QFont

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


# defining the system message
system_message_template = "<|im_start|>system\n{}\n<|im_end|>"
system_message_instance = system_message_template.format("You are an AI assistant that helps people find information.")


# create the main application window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # initialize the parameters
        self.model = default_model
        self.callback_num = default_callback_num

        self.setWindowTitle("GPT Chat")
        self.resize(1000, 1000)

        # create the chat display widget
        # font = QFont('Microsoft YaHei', 12)
        font = QFont('Arial', 12)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(font)

        # create the user input widget
        self.user_input = QTextEdit()
        # self.user_input.setFixedSize(400, 300)
        self.user_input.setFont(font)
        self.user_input.setAcceptRichText(False)
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

        # create the clear button
        self.clear_button = QPushButton('Clear history')
        self.clear_button.clicked.connect(self.clear_history)

        # create a dropdown menu for model
        self.comboBox_model = QComboBox(self)
        for model_name in model_names:
            self.comboBox_model.addItem(model_name)
        self.comboBox_model.activated[str].connect(self.onModelSelectionActivated)

        # create a label to display the selected model
        self.label_model = QLabel(self)
        self.label_model.setText(f"Selected model:")

        # create a dropdown menu for history length
        self.comboBox_history = QComboBox(self)
        for i in range(1, 11):
            self.comboBox_history.addItem(str(i))
        self.comboBox_history.addItem(str(999))
        self.comboBox_history.setCurrentIndex(self.callback_num - 1)
        self.comboBox_history.activated[str].connect(self.onHistoryLengthSelectionActivated)

        # create a label to display the selected model
        self.label_history = QLabel(self)
        self.label_history.setText(f"History length:")

        # create the layout
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        # layout.addWidget(self.chat_display)
        input_layout = QHBoxLayout()
        # input_layout.addWidget(self.user_input)
        input_layout.addWidget(self.submit_button)
        input_layout.addWidget(self.label_model)
        input_layout.addWidget(self.comboBox_model)
        input_layout.addWidget(self.label_history)
        input_layout.addWidget(self.comboBox_history)
        input_layout.addWidget(self.clear_button)
        layout.addLayout(input_layout)

        # create the widget to hold the layout
        widget = QWidget()
        widget.setLayout(layout)

        # set the main window widget
        self.setCentralWidget(widget)

        # initialize the messages list
        self.messages = []

    # dropdown menu activated function - model selection
    def onModelSelectionActivated(self, text):
        # call the selected GPT model based on the user's selection
        self.model = text
        # self.label_model.setText(f"Selected model: {text}")
        self.chat_display.append(f"Current model changed to: {text}")

    # dropdown menu activated function - model selection
    def onHistoryLengthSelectionActivated(self, text):
        # call the selected GPT model based on the user's selection
        self.callback_num = int(text)
        # self.label_model.setText(f"Selected model: {text}")
        self.chat_display.append(f"Current history changed to: {text}")

    def clear_history(self):
        self.messages = []
        self.chat_display.clear()
        self.chat_display.append(f"Chat history cleared. You can begin a new chat session.")

    # function to handle user input
    def on_user_input(self):
        # get the user input
        user_input = self.user_input.toPlainText()

        # clear the user input widget
        self.user_input.setText("")
        # update the chat display widget
        self.chat_display.setTextColor(user_input_color)
        self.chat_display.append("You: " + user_input)
        self.chat_display.setTextColor(system_message_color)

        # add the user message to the messages list
        self.messages.append({"sender": "user", "text": user_input})
        print(user_input)

        # generate the AI response
        response = openai.Completion.create(
            engine=self.model,
            prompt=create_prompt(system_message_instance, self.messages),
            temperature=0.5,
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
        if len(self.messages) > self.callback_num * 2:
            self.messages = self.messages[-(self.callback_num * 2):]

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
