import os

l1 = ("# SPDX-FileCopyrightText:", "// SPDX-FileCopyrightText:")
l2 = ("#\n", "//\n")
l3 = ("# SPDX-License-Identifier:", "// SPDX-License-Identifier:")

files = []

missing = []
has = []


for r, d, f in os.walk("."):
    for file in f:
        if file.split('.')[-1] in ("py", "cpp", "ino", "h"):
            files.append(os.path.join(r, file))

for file in files:
    with open(file, "r") as F:
        lines = F.readlines()[0:3]
        if len(lines) == 3 and "SPDX-FileCopyrightText:" not in lines[0]:
            missing.append(file)
        else:
            has.append(file)

print(
    f"{len(missing)} Missing SPDX\n{len(has)} Have SPDX ({100*len(has)/len(files):.2f}%)"
)
with open('missing.txt', 'w') as F:
    for i in missing:
        F.write(i+'\n')

with open('has.txt', 'w') as F:
    for i in has:
        F.write(i+'\n')

for file in missing:
    os.system(f"grep -irHn 'author' {file}")
