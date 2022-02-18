import subprocess
import os

l2 = "#\n"
l2_ = "//\n"
l3 = "# SPDX-License-Identifier: MIT\n"
l3_ = "// SPDX-License-Identifier: MIT\n"

with open('missing.txt', 'r') as F:
    lines = F.readlines()
    todo = lines[0:20]
    write = lines[20:]

todo = [f[:-1] for f in todo]
print(todo)
"""
with open('missing.txt', 'w') as F:
    f.write(write)
"""

for file in todo:
    os.system(f'git log --follow {file}')
    year = input("Year: ")
    author = input("Author: ")

    with open(file, 'r') as F:
        text = F.read()
    with open(file, 'w') as F:
        print(file[-2:])
        if file[-2:] == 'py':
            l1 = f"# SPDX-FileCopyrightText: {year} {author} for Adafruit Industries\n"
            F.write(l1)
            F.write(l2)
            F.write(l3)
        else:
            l1_ = f"// SPDX-FileCopyrightText: {year} {author} for Adafruit Industries\n"
            F.write(l1_)
            F.write(l2_)
            F.write(l3_)
        F.write(text)

    os.system(f'vi {file}')
    input()
