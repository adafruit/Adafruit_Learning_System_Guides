"""
Class that handles the input and calculations
"""
class Calculator:
    def __init__(self, calc_display, clear_button, label_offset):
        self._calc_display = calc_display
        self._clear_button = clear_button
        self._label_offset = label_offset
        self.all_clear()

    def calculate(self, number_one, operator, number_two):
        result = eval(number_one + operator + number_two)
        if int(result) == result:
            result = int(result)
        return str(result)

    def all_clear(self):
        self._accumulator = "0"
        self._operator = None
        self._equal_pressed = False
        self.clear_entry()

    def clear_entry(self):
        self._operand = None
        self._set_button_ce(False)
        self._set_text("0")

    def _set_button_ce(self, entry_only):
        if entry_only:
            self._clear_button.label = "CE"
        else:
            self._clear_button.label = "AC"

    def _set_text(self, text):
        self._calc_display.text = text
        _, _, screen_w, _ = self._calc_display.bounding_box
        self._calc_display.x = self._label_offset - screen_w

    def _get_text(self):
        return self._calc_display.text

    def add_input(self, input):
        try:
            if input == "AC":
                self.all_clear()
            elif input == "CE":
                self.clear_entry()
            elif self._operator is None and input == "0":
                pass
            elif len(input) == 1 and 48 <= ord(input) <= 57:
                display_text = self._get_text()
                if self._operand is None and self._operator is not None:
                    display_text = ""
                elif self._operand is not None and self._operator is not None and self._equal_pressed:
                    self._accumulator = self._operand
                    self._operator = None
                    self._operand = None
                    display_text = ""
                elif display_text == "0":
                    display_text = ""
                display_text += input
                self._set_text(display_text)
                if self._operator is not None:
                    self._operand = display_text
                self._set_button_ce(True)
                self._equal_pressed = False
            elif input in ('+', '-', '/', 'x'):
                if input == "x":
                    input = "*"
                if self._equal_pressed:
                    self._operand = None
                if self._operator is None:
                    self._operator = input
                else:
                    # Perform current calculation before changing inputs
                    if self._operand is not None:
                        self._accumulator = self.calculate(self._accumulator, self._operator, self._operand)
                        self._set_text(self._accumulator)
                    self._operand = None
                    self._operator = input
                self._accumulator = self._get_text()
                self._equal_pressed = False
            elif input == ".":
                if not input in self._get_text():
                    self._set_text(self._get_text() + input)
                    self._set_button_ce(True)
                    self._equal_pressed = False
            elif input == "+/-":
                self._set_text(self.calculate(self._get_text(), "*", "-1"))
            elif input == "%":
                self._set_text(self.calculate(self._get_text(), "/", "100"))
            elif input == "=":
                if self._operator is not None:
                    if self._operand is None:
                        self._operand = self._get_text()
                    self._accumulator = self.calculate(self._accumulator, self._operator, self._operand)
                self._set_text(self._accumulator)
                self._equal_pressed = True
        except (ZeroDivisionError, RuntimeError):
            self.all_clear()
            self._set_text("Error")
