import socket
import threading
import os
from tkinter import *
from tkinter import filedialog, ttk, scrolledtext
from PIL import Image, ImageTk
from server.mycompression import MediaCompressor
import sounddevice as sd
from scipy.io.wavfile import write
import cv2
from datetime import datetime


compressor = MediaCompressor()

HOST = "trolley.proxy.rlwy.net"
PORT = 46499
HEADER_SIZE = 256

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.settimeout(10)
    client.connect((HOST, PORT))
    client.settimeout(None)
    print("Connected successfully to Railway!")
except Exception as e:
    print(f"Failed to connect: {e}")


screen = Tk()
screen.title("Chat Application")
screen.geometry("540x620")
# for zoom + or -
screen.rowconfigure(0, weight=1)
screen.columnconfigure(0, weight=1)

hd_mode = BooleanVar()


msg_area = scrolledtext.ScrolledText(
    screen,
    wrap=WORD,
    font=("Arial", 11),
    state="disabled",
)
msg_area.grid(row=0, column=0, columnspan=6, padx=10, pady=10, sticky="nsew")

progress = ttk.Progressbar(
    screen,
    orient="horizontal",
    length=300,
    mode="determinate",
)
progress.grid(row=3, column=0, columnspan=6, padx=10, pady=5, sticky="ew")


status_var = StringVar(value="")
status_label = Label(screen, textvariable=status_var, font=("Arial", 9), fg="gray")
status_label.grid(row=4, column=0, columnspan=6, pady=(0, 4))


entry = Entry(screen, font=("Arial", 12))
entry.grid(row=2, column=0, columnspan=5, padx=(10, 5), pady=10, sticky="ew")

entry.bind("<Return>", lambda _e: send_text())




def add_message(text, side="left"):
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{current_time}] {text}\n"

    def _insert():
        msg_area.config(state="normal")
        msg_area.tag_config("left", justify="left")
        msg_area.tag_config("right", justify="right")
        msg_area.insert(END, formatted, side)
        msg_area.see(END)
        msg_area.config(state="disabled")

    screen.after(0, _insert)


def recv_exact(sock, size):
    
    data = b""
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None
        data += packet
    return data


def _update_progress(value, maximum=None, label=""):
    
    def _do():
        if maximum is not None:
            progress["maximum"] = maximum
        progress["value"] = value
        status_var.set(label)
        screen.update_idletasks()
    screen.after(0, _do)



def _send_file_bytes(path, file_type, display_name=None):

    
    filename = os.path.basename(path)
    filesize = os.path.getsize(path)

    header = f"FILE|{file_type}|{filename}|{filesize}"
    client.sendall(header.encode().ljust(HEADER_SIZE, b" "))

    sent = 0
    _update_progress(0, filesize, f"Sending {filename}…")

    with open(path, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            client.sendall(chunk)
            sent += len(chunk)
            _update_progress(sent, label=f"Sending {filename}… {sent * 100 // filesize}%")

    _update_progress(0, label="")
    label = display_name or filename
    add_message(f"You sent {label}", "left")


def send_text():
    text = entry.get().strip()
    if not text:
        return

    data = text.encode()
    header = f"TEXT|{len(data)}".encode().ljust(HEADER_SIZE, b" ")
    client.sendall(header)
    client.sendall(data)

    add_message("You: " + text, "left")
    entry.delete(0, END)


def send_file(file_type):
    types = {
        "image": [("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.gif")],
        "video": [("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv")],
    }.get(file_type, [("All files", "*.*")])

    path = filedialog.askopenfilename(filetypes=types)
    if not path:
        return

    send_path = path if hd_mode.get() else compressor.compress_file(path)

    
    threading.Thread(
        target=_send_file_bytes,
        args=(send_path, file_type),
        daemon=True,
    ).start()


def capture_camera():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        add_message("⚠️ Camera not found")
        return

    ret, frame = cap.read()
    cap.release()
    cv2.destroyAllWindows()

    if not ret:
        add_message("⚠️ Failed to capture image")
        return

    filename = f"camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    cv2.imwrite(filename, frame)

    threading.Thread(
        target=_send_file_bytes,
        args=(filename, "image", "camera photo"),
        daemon=True,
    ).start()


def record_voice():
    fs = 44100
    seconds = 5

    add_message("🎤 Recording for 5 seconds…")

    def _record():
        recording = sd.rec(int(seconds * fs), samplerate=fs, channels=2)
        sd.wait()
        filename = f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        write(filename, fs, recording)
        add_message("✅ Recording done — sending…")
        _send_file_bytes(filename, "audio", "voice message")

    threading.Thread(target=_record, daemon=True).start()




def receive_messages():
    while True:
        try:
            raw_header = recv_exact(client, HEADER_SIZE)
            if not raw_header:
                break

            header = raw_header.decode().strip()
            parts = header.split("|")
            msg_type = parts[0]

            if msg_type == "TEXT":
                size = int(parts[1])
                data = recv_exact(client, size)
                text = data.decode()
                add_message("Friend: " + text, "right")

            elif msg_type == "FILE":
                file_type = parts[1]
                filename = parts[2]
                filesize = int(parts[3])

                folder = "received"
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, filename)

                received = 0
                _update_progress(0, filesize, f"Receiving {filename}…")

                with open(path, "wb") as f:
                    while received < filesize:
                        chunk = client.recv(min(4096, filesize - received))
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)
                        _update_progress(
                            received,
                            label=f"Receiving {filename}… {received * 100 // filesize}%",
                        )

                _update_progress(0, label="")
                
                add_message(f"Received {file_type}: {filename}", "right")

        except Exception as exc:
            print(f"Receive error: {exc}")
            break




img_btn = Button(screen, text="🖼 Image", command=lambda: send_file("image"))
img_btn.grid(row=1, column=0, padx=4, pady=5, sticky="w")

video_btn = Button(screen, text="🎬 Video", command=lambda: send_file("video"))
video_btn.grid(row=1, column=1, padx=4, pady=5)

file_btn = Button(screen, text="📎 File", command=lambda: send_file("file"))
file_btn.grid(row=1, column=2, padx=4, pady=5)

hd_btn = Checkbutton(screen, text="HD", variable=hd_mode)
hd_btn.grid(row=1, column=3, padx=4, pady=5)

camera_btn = Button(screen, text="📷 Camera", command=capture_camera)
camera_btn.grid(row=1, column=4, padx=4, pady=5)

voice_btn = Button(screen, text="🎤 Voice", command=record_voice)
voice_btn.grid(row=1, column=5, padx=4, pady=5)


send_btn = Button(screen, text="Send", bg="#534AB7", fg="white", command=send_text)
send_btn.grid(row=2, column=5, padx=(0, 10), pady=10)


thread = threading.Thread(target=receive_messages, daemon=True)
thread.start()

screen.mainloop()