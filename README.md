# 🔐 Python Keylogger — Digital Forensics Academic Project

> **Academic Purpose Only** — This project was developed as part of a Digital Forensics course to understand how keyloggers work, how they can be detected, and how to defend against them.

---

## 📌 Overview

This is a Python-based keylogger built for educational purposes in a Digital Forensics lab environment. It demonstrates how malicious software can capture keystrokes, track active windows, encrypt captured data, and exfiltrate it via email — techniques commonly studied in forensics and cybersecurity curricula.

---

## ⚙️ Features

- **Keystroke capture** — Records all keystrokes including special keys (Enter, Backspace, Tab, Arrow keys, etc.)
- **Active window tracking** — Logs which application was active when keys were pressed
- **Fernet encryption** — Captured logs are encrypted at rest using symmetric encryption
- **Email exfiltration** — Automatically sends logs via Gmail SMTP (port 587/465) at configurable intervals
- **Auto key management** — Generates and stores encryption key locally
- **Thread-safe logging** — Uses mutex locks to prevent race conditions
- **Graceful exit** — Final log flush on ESC key press

---

## 🛠️ Technologies Used

| Library | Purpose |
|---|---|
| `pynput` | Keyboard event listener |
| `cryptography (Fernet)` | Symmetric encryption of log data |
| `smtplib` | Email transmission via SMTP |
| `pygetwindow` | Active window title tracking |
| `threading` | Concurrent auto-send loop |

---
