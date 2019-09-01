def ellipsis(s: str, length: int = 80, take_from: str = "start") -> str:
    if len(s) <= length:
        return s
    if take_from == "start":
        return s[:(length)] + "..."
    elif take_from == "end":
        return "..." + s[((length) * -1) :]
    elif take_from == "middle":
        if len(s) < 10:
            return ellipsis(s, length, take_from="start")
        sides = (length + 6) // 2
        return "..." + s[sides : (len(s) - sides)] + "..."
