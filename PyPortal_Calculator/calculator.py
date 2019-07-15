"""
CircuitPython library to handle the input and calculations

* Author(s): Melissa LeBlanc-Williams
"""

# pylint: disable=eval-used
def calculate(number_one, operator, number_two):
    result = eval(number_one + operator + number_two)
    if int(result) == result:
        result = int(result)
    return str(result)

class Calculator:
    def __init__(self, calc_display, clear_button, label_offset):
        self._error = False
        self._calc_display = calc_display
        self._clear_button = clear_button
        self._label_offset = label_offset
        self._accumulator = "0"
        self._operator = None
        self._equal_pressed = False
        self._operand = None
        self._all_clear()

    def get_current_operator(self):
        operator = self._operator
        if operator == "*":
            operator = "x"
        return operator

    def _all_clear(self):
        self._accumulator = "0"
        self._operator = None
        self._equal_pressed = False
        self._clear_entry()

    def _clear_entry(self):
        self._operand = None
        self._error = False
        self._set_button_ce(False)
        self._set_text("0")

    def _set_button_ce(self, entry_only):
        self._clear_button.selected = False
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

    def _handle_number(self, input_key):
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
        display_text += input_key
        self._set_text(display_text)
        if self._operator is not None:
            self._operand = display_text
        self._set_button_ce(True)
        self._equal_pressed = False

    def _handle_operator(self, input_key):
        if input_key == "x":
            input_key = "*"
        if self._equal_pressed:
            self._operand = None
        if self._operator is None:
            self._operator = input_key
        else:
            # Perform current calculation before changing input_keys
            if self._operand is not None:
                self._accumulator = calculate(self._accumulator, self._operator, self._operand)
                self._set_text(self._accumulator)
            self._operand = None
            self._operator = input_key
        self._accumulator = self._get_text()
        self._equal_pressed = False

    def _handle_equal(self):
        if self._operator is not None:
            if self._operand is None:
                self._operand = self._get_text()
            self._accumulator = calculate(self._accumulator, self._operator, self._operand)
        self._set_text(self._accumulator)
        self._equal_pressed = True

    def _update_operand(self):
        if self._operand is not None:
            self._operand = self._get_text()

    def add_input(self, input_key):
        try:
            if self._error:
                self._clear_entry()
            elif input_key == "AC":
                self._all_clear()
            elif input_key == "CE":
                self._clear_entry()
            elif self._operator is None and input_key == "0":
                pass
            elif len(input_key) == 1 and 48 <= ord(input_key) <= 57:
                self._handle_number(input_key)
            elif input_key in ('+', '-', '/', 'x'):
                self._handle_operator(input_key)
            elif input_key == ".":
                if not input_key in self._get_text():
                    self._set_text(self._get_text() + input_key)
                    self._set_button_ce(True)
                    self._equal_pressed = False
            elif input_key == "+/-":
                self._set_text(calculate(self._get_text(), "*", "-1"))
                self._update_operand()
            elif input_key == "%":
                self._set_text(calculate(self._get_text(), "/", "100"))
                self._update_operand()
            elif input_key == "=":
                self._handle_equal()
        except (ZeroDivisionError, RuntimeError):
            self._all_clear()
            self._error = True
            self._set_text("Error")
