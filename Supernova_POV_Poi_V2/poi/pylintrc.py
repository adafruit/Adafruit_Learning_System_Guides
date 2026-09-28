[MASTER]
ignore=CVS
jobs=2
persistent=yes
unsafe-load-any-extension=no

[MESSAGES CONTROL]
# CircuitPython libs (board/digitalio/adafruit_*) won't import on desktop Python.
# If you're linting on your Mac (not on-device), keep import-error disabled.
disable=
    import-error,
    too-many-instance-attributes,
    len-as-condition,
    too-few-public-methods,
    anomalous-backslash-in-string,
    no-else-return,
    simplifiable-if-statement,
    too-many-arguments,
    duplicate-code,
    no-name-in-module,
    no-member,
    missing-docstring,
    invalid-name,
    consider-using-enumerate,
    unexpected-keyword-arg

[REPORTS]
reports=no
score=yes
output-format=text
msg-template={path}:{line}: {msg} ({symbol})
evaluation=10.0 - ((float(5 * error + warning + refactor + convention) / statement) * 10)

[FORMAT]
max-line-length=100
expected-line-ending-format=LF
ignore-long-lines=^\s*(# )?<?https?://\S+>?$

[TYPECHECK]
ignore-mixin-members=yes
ignore-on-opaque-inference=yes
missing-member-hint=yes
missing-member-hint-distance=1
missing-member-max-choices=1

[DESIGN]
max-args=5
max-attributes=11
max-bool-expr=5
max-branches=12
max-locals=15
max-parents=7
max-public-methods=20
max-returns=6
max-statements=50
min-public-methods=1

[EXCEPTIONS]
overgeneral-exceptions=builtins.Exception
