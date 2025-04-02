# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

class DataBuffer:
    def __init__(self):
        self._dataset = {}
        self._default_data = {}

    def set_data_structure(self, data_structure):
        self._default_data = data_structure
        self.reset()

    def reset(self, field=None):
        # Copy the default data to the dataset
        if field is not None:
            if not isinstance(field, (tuple, list)):
                field = [field]
            for item in field:
                self._dataset[item] = self.deepcopy(self._default_data[item])
        else:
            self._dataset = self.deepcopy(self._default_data)

    def deepcopy(self, data):
        # Iterate through the data and copy each element
        new_data = {}
        if isinstance(data, (dict)):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    new_data[key] = self.deepcopy(value)
                else:
                    new_data[key] = value
        elif isinstance(data, (list)):
            for idx, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    new_data[idx] = self.deepcopy(item)
                else:
                    new_data[idx] = item
        return new_data

    @property
    def dataset(self):
        return self._dataset
