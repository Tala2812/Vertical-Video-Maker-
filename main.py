import os
import sys
from tkinter import filedialog, Tk
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips, ColorClip, VideoFileClip
from PIL import Image, ImageFont, ImageDraw
import argparse

# Настройки по умолчанию
DEFAULT_BACKGROUND = (255, 255, 255)  # Белый фон
DEFAULT_OUTPUT = "output.mp4"
DEFAULT_DURATION = 4
DEFAULT_FPS = 30


def select_files():
    """Открывает диалог выбора файлов"""
    root = Tk()
    root.withdraw()  # Скрываем основное окно

    # Выбор изображений
    images = filedialog.askopenfilenames(
        title="Выберите изображения",
        filetypes=[("Изображения", "*.jpg *.jpeg *.png")]
    )

    # Выбор аудио
    audio = filedialog.askopenfilename(
        title="Выберите аудиофайл",
        filetypes=[("Аудио", "*.mp3 *.wav")]
    )

    return list(images), audio


def create_cover(image_path, output_size=(1080, 1920)):
    """Создает обложку из первого изображения"""
    img = Image.open(image_path)
    img.thumbnail((output_size[0], output_size[1]), Image.LANCZOS)

    background = Image.new('RGB', output_size, DEFAULT_BACKGROUND)
    position = (
        (output_size[0] - img.size[0]) // 2,
        (output_size[1] - img.size[1]) // 2
    )
    background.paste(img, position)

    # Добавляем текст (опционально)
    try:
        draw = ImageDraw.Draw(background)
        font = ImageFont.load_default()
        draw.text((50, 50), "Моя обложка", fill=(0, 0, 0), font=font)
    except:
        pass

    cover_path = "cover.jpg"
    background.save(cover_path)
    return cover_path


def process_image(image_path, output_size=(1080, 1920)):
    """Обрабатывает изображение с белым фоном"""
    img = Image.open(image_path)
    width, height = img.size
    target_width, target_height = output_size
    img_ratio = width / height
    target_ratio = target_width / target_height

    if img_ratio > target_ratio:
        new_width = target_width
        new_height = int(target_width / img_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * img_ratio)

    img = img.resize((new_width, new_height), Image.LANCZOS)
    background = Image.new('RGB', output_size, DEFAULT_BACKGROUND)
    position = (
        (target_width - new_width) // 2,
        (target_height - new_height) // 2
    )
    background.paste(img, position)

    temp_path = f"temp_{os.path.basename(image_path)}"
    background.save(temp_path)
    return temp_path

processed_images = []
images = []
for img in images:
    processed_path = process_image(img)
    processed_images.append(processed_path)

print("Обработанные изображения:")
for img in processed_images:
    print(img)
    try:
        with Image.open(img) as im:
            print("Размер:", im.size)
    except Exception as e:
        print(f"Ошибка открытия изображения {img}: {e}")


def create_video(images, audio_path, output_path=DEFAULT_OUTPUT, duration=DEFAULT_DURATION, fps=DEFAULT_FPS):
    # Создаем обложку из первого изображения
    if images:
        cover_path = create_cover(images[0])
        images = [cover_path] + images

    processed_images = []
    for img_path in images:
        try:
            processed_path = process_image(img_path)
            processed_images.append(processed_path)
        except Exception as e:
            print(f"Ошибка обработки {img_path}: {e}")

    if not processed_images:
        raise ValueError("Нет изображений для создания видео")

    # Показываем каждую картинку одинаковое время, чтобы итоговое видео длилось duration секунд
    total_duration = duration * len(processed_images)  # Суммарная длина видео
    video_clip = ImageSequenceClip(processed_images, durations=[duration] * len(processed_images))

    duration_per_image = duration / len(processed_images)
    video_clip = ImageSequenceClip(processed_images, durations=[duration_per_image] * len(processed_images))

    if audio_path:
        audio_clip = AudioFileClip(audio_path)
        # Подгоняем аудио к длине видео
        if audio_clip.duration < video_clip.duration:
            audio_clip = audio_clip.loop(duration=video_clip.duration)
        else:
            audio_clip = audio_clip.subclip(0, video_clip.duration)
        video_clip = video_clip.set_audio(audio_clip)  # ВАЖНО: set_audio

    video_clip.write_videofile(
        output_path,
        fps=fps,
        codec='libx264',
        audio_codec='aac',
        threads=4,
        preset='fast'
    )

    # Удаляем временные файлы
    for img_path in processed_images + [cover_path]:
        try:
            os.remove(img_path)
        except Exception as ex:
            print(f"Не удалось удалить {img_path}: {ex}")


def main():
    images = []
    audio = None
    try:
        print("1. Выбрать файлы через диалог")
        print("2. Использовать тестовые файлы")
        choice = input("Выберите вариант (1/2): ").strip()

        if choice == "1":
            images, audio = select_files()
            if not images:
                raise ValueError("Не выбраны изображения")
            if not audio:
                print("Аудиофайл не выбран. Видео будет без звука.")
        elif choice == "2":
            images = [
                r"C:\Users\Константин\Pictures\Saved Pictures\photo1.jpg.jpg",
                r"C:\Users\Константин\Pictures\Saved Pictures\photo2.jpg.jpg",
                r"C:\Users\Константин\Pictures\Saved Pictures\photo3.jpg.jpg",
                r"C:\Users\Константин\Pictures\Saved Pictures\photo4.jpg.jpg",
                r"C:\Users\Константин\Pictures\Saved Pictures\photo5.jpg.jpg"
            ]
            audio = r"C:\Users\Константин\Music\music.test.mp3"
        else:
            raise ValueError("Неверный выбор варианта")

        output = input(f"Имя выходного файла ({DEFAULT_OUTPUT}): ") or DEFAULT_OUTPUT
        duration = float(input(f"Длительность кадра ({DEFAULT_DURATION} сек): ") or DEFAULT_DURATION)
        fps = int(input(f"Частота кадров ({DEFAULT_FPS} FPS): ") or DEFAULT_FPS)

        if not images:
            raise ValueError("Нет изображений для создания видео")

        create_video(images, audio, output, duration, fps)
        print(f"Видео успешно создано: {output}")

    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        if sys.platform == "win32":
            os.system("pause")

if __name__ == "__main__":
    main()


