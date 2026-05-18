from PIL import Image
from moviepy import VideoFileClip
import os



class MediaCompressor:
    def compress_image(self, input_path, output_path):
        img = Image.open(input_path)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        img.save(output_path, "JPEG", quality=50)

    def compress_video(self, input_path, output_path):
        clip = VideoFileClip(input_path)

        clip.write_videofile(
            output_path,
            bitrate="500k",
            logger=None
        )

        clip.close()

    def compress_file(self, path):
        ext = os.path.splitext(path)[1].lower()

        image_exts = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]
        video_exts = [".mp4", ".avi", ".mov", ".mkv"]

        folder = "temp"

        if not os.path.exists(folder):
            os.makedirs(folder)

        if ext in image_exts:
            output = os.path.join(folder, "compressed.jpg")
            self.compress_image(path, output)
            return output

        elif ext in video_exts:
            output = os.path.join(folder, "compressed.mp4")
            self.compress_video(path, output)
            return output

        return path