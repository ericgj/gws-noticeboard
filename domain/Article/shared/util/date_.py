from datetime import datetime


def encode(d):
    return d.strftime("%Y-%m-%d")


def decode(s):
    return datetime.strptime(s, "%Y-%m-%d").date()
