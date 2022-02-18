import subprocess
import os
import re

l2 = "#\n"
l2_ = "//\n"
l3 = "# SPDX-License-Identifier: MIT\n\n"
l3_ = "// SPDX-License-Identifier: MIT\n\n"

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

def log_format(file):
    cmd = f'git log --shortstat --follow --pretty=format:"%n%H%n%Cred%an%Creset (%ae) %Cblue%as%Creset%n%s%n" {file}'
    log = str(subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read())[2:-1].replace("\\t", "\t").replace("\\n\\n", "\n").replace("\\n", "\n").split("\n")

    log.insert(0, file[2:])

    long = max(log, key=len)
    long = len(long)
    print("┌" + "─" * (long + 4) + "┐")
    for line in log:
        start = len(line)
        if re.search(r"\d\d\d\d-\d\d-\d\d", line):
            line = re.split(r'\s[(]|[)]\s', line)
            default_year = line[2].split('-')[0]
            default_author = line[0]
            line = f"\033[94m\033[1m{line[0]}\033[0m ({line[1]}) \033[96m\033[1m{line[2]}\033[0m"
            print("│ ", line, " " * (long - (start)), "│")

        elif "changed" in line and ("insert" in line or "delet" in line):
            line = line.split()
            if len(line) == 7:
                length = len(f"{line[3]} {line[4]} {line[5]} {line[6]}")
                line = f"\033[92m\033[1m{line[3]}\033[0m {line[4]} \033[91m\033[1m{line[5]}\033[0m {line[6]}"
                print("│ ", line, " " * (long - (len(line) - 26)), "│")
            elif "insert" in line[4]:
                line = f"\033[92m{line[3]}\033[0m {line[4]}"
                print("│ ", line, " " * (long - (len(line) - 9)), "│")
            else:
                line = f"\033[91m{line[3]}\033[0m {line[4]}"
                print("│ ", line, " " * (long - (len(line) - 9)), "│")
        else:
            print("│ ", line, " " * (long - len(line)), "│")
    print("└" + "─" * (long + 4) + "┘")
    return default_year, default_author

for file in todo:
    os.system('clear')

    default_year, default_author = log_format(file)

    year = input(f"Year [{default_year}]: ")
    if not year:
        year = default_year
    author = input(f"Author [{default_author}]: ")
    if not author:
        author = default_author

    with open(file, 'r') as F:
        text = F.read()
    with open(file, 'w') as F:
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
    input("Next")

for i in todo:
    print(i)
