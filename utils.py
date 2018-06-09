import os
import sys

def read_file(filename):
    content = None
    with open(filename, 'r', encoding="utf8") as file:
        content = file.read()
    return content


def write_file(filename, text):
    with open(filename, 'w', encoding='utf8') as f:
        f.write(text)


