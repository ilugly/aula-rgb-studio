"""AULA 2.4G RGB reports, shared by Windows and macOS."""


def pkt(cmd, total, idx, sub, chunk):
    report = bytearray(20)
    report[:5] = (0x13, cmd, total, idx, ((sub << 4) | len(chunk)) & 0xFF)
    report[5:5 + len(chunk)] = chunk
    report[19] = sum(report[:19]) & 0xFF
    return bytes(report)


def split(cmd, sub, data):
    chunks = [data[i:i + 14] for i in range(0, len(data), 14)] or [b""]
    return [pkt(cmd, len(chunks), i, sub, chunk) for i, chunk in enumerate(chunks)]
