# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT

from displayio import Group
from adafruit_display_shapes.rect import Rect
from eventbutton import EventButton

MENU_ITEM_HEIGHT = 16

class Menu(Group):
    def handle_mouse(self, point, clicked, waiting_for_release):
        if waiting_for_release:
            return False
        # Check if the point is in the menu items group
        handled_submenu = None
        for submenu in self:
            if isinstance(submenu, SubMenu):
                if submenu.handle_mouse(point, clicked):
                    handled_submenu = submenu
        if clicked:
            # Hide any visible menus
            for submenu in self:
                if isinstance(submenu, SubMenu) and submenu != handled_submenu:
                    submenu.hide()
        return handled_submenu is not None

class SubMenu(Group):
    def __init__(self, label, button_width, menu_width, x, y):
        super().__init__()
        self._label = label
        self._button_width = button_width
        self._menu_width = menu_width
        self._menu_items_group = None
        self._xpos = x
        self._ypos = y
        self._menu_items = []
        self._root_button = None

    def add_item(self, function, label, selected=False):
        key = label.lower().replace(" ", "_")
        self._menu_items.append(
            {
                "key": key,
                "function": function,
                "label": label,
                "selected": selected,
            }
        )
        self._render()

    def select_item(self, key):
        print(f"selecting {key}")
        for item in self._menu_items:
            if item["key"] == key:
                item["selected"] = True
            else:
                item["selected"] = False
        self._render()

    @staticmethod
    def _create_button(callback, label, width, x, y=0, border=True, selected=False):
        if border:
            outline_color = 0x000000
            selected_outline = 0x333333
        else:
            outline_color = 0xEEEEEE
            selected_outline = 0xBBBBBB

        if selected:
            label_color = 0x008800
        else:
            label_color = 0x333333

        button = EventButton(
            callback,
            x=x,
            y=y,
            width=width,
            height=MENU_ITEM_HEIGHT,
            label=label,
            style=EventButton.RECT,
            fill_color=0xEEEEEE,
            outline_color=outline_color,
            label_color=label_color,
            selected_fill=0xBBBBBB,
            selected_label=0x333333,
            selected_outline=selected_outline,
        )
        return button


    def _toggle_submenu(self):
        self._menu_items_group.hidden = not self._menu_items_group.hidden

    def _render(self):
        # Redraw the menu
        # Remove all existing elements contained inside of this class
        while len(self) > 0:
            self.pop()

        # create a new root button
        self._root_button = self._create_button(
            self._toggle_submenu,
            self._label,
            self._button_width,
            self._xpos,
            self._ypos,
            True,
        )
        self.append(self._root_button)

        # Create the menu items group
        self._menu_items_group = Group()
        self._menu_items_group.hidden = True
        self.append(self._menu_items_group)

        # Add the background rectangle to the menu items group
        self._menu_items_group.append(
            Rect(self._xpos, self._ypos + self._root_button.height - 1, self._menu_width,
                len(self._menu_items) * MENU_ITEM_HEIGHT + 2,
                fill=0xEEEEEE,
                outline=0x333333
            )
        )

        # Add the menu items to the menu items group
        for index, item in enumerate(self._menu_items):
            button = self._create_button(
                item["function"],
                item["label"],
                self._menu_width - 2,
                self._xpos + 1,
                self._ypos + index * MENU_ITEM_HEIGHT + self._root_button.height,
                False,
                item["selected"],
            )
            self._menu_items_group.append(button)

    def hide(self):
        self._menu_items_group.hidden = True

    def handle_mouse(self, point, clicked):
        # Check if the point is in the root button
        if self._menu_items_group.hidden:
            if self._root_button.contains(point):
                self._root_button.selected = True
                if clicked:
                    self._root_button.click()
                    return True
            else:
                self._root_button.selected = False
        else:
            # Check if the point is in the menu items group
            for button in self._menu_items_group:
                if isinstance(button, EventButton):
                    if button.contains(point):
                        button.selected = True
                        if clicked:
                            button.click()
                            self._menu_items_group.hidden = True
                            return True
                    else:
                        button.selected = False
        return False

    @property
    def visible(self):
        return not self._menu_items_group.hidden

    @property
    def items_group(self):
        return self._menu_items_group

    @property
    def items(self):
        return self._menu_items
