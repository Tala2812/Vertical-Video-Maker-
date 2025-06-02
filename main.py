import os
import sys
from tkinter import filedialog, Tk, messagebox, simpledialog
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips, ColorClip, VideoFileClip, \
    CompositeVideoClip, vfx

from PIL import Image, ImageFont, ImageDraw, ImageFilter
import argparse
from enum import Enum

# Настройки по умолчанию
DEFAULT_OUTPUT = "output.mp4"
DEFAULT_DURATION = 4
DEFAULT_FPS = 30
BLUR_RADIUS = 20  # Радиус размытия фона
TRANSITION_DURATION = 0.5  # Длительность перехода в секундах


class TransitionType(Enum):
    FADE = 1
    SLIDE_RIGHT = 2
    SLIDE_DOWN = 3



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


def select_transition_type():
    """Диалог выбора типа перехода между слайдами"""
    root = Tk()
    root.withdraw()

    choice = simpledialog.askinteger(
        "Выбор перехода",
        "Выберите тип перехода:\n"
        "1. Плавное затухание\n"
        "2. Сдвиг вправо\n"
        "3. Сдвиг вниз\n"
        
        
    

        "Введите номер (1-3):",
        minvalue=1,
        maxvalue=3,
        initialvalue=1
    )

    transitions = [
        TransitionType.FADE,
        TransitionType.SLIDE_RIGHT,
        TransitionType.SLIDE_DOWN,


    ]

    if choice and 1 <= choice <= 3:
        return transitions[choice - 1]
    return TransitionType.FADE


def create_cover(image_path, output_size=(1080, 1920)):
    img = Image.open(image_path)
    img.thumbnail((output_size[0], output_size[1]), Image.LANCZOS)

    # Создаем размытый фон
    bg = img.copy().resize(output_size).filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
    bg.paste(img, ((output_size[0] - img.width) // 2, (output_size[1] - img.height) // 2))

    # Диалог для текста
    root = Tk()
    root.withdraw()
    custom_text = simpledialog.askstring("Текст обложки",
                                         "Введите текст для обложки:",
                                         initialvalue="Моя обложка")
    root.destroy()

    # Если текст ввели (не нажали Cancel)
    if custom_text:
        try:
            draw = ImageDraw.Draw(bg)
            font = ImageFont.truetype("arial.ttf", 60)

            # Красивое оформление с тенью
            shadow_color = (0, 0, 0, 150)
            for i in [(x, y) for x in (-2, 0, 2) for y in (-2, 0, 2) if x or y]:
                draw.text((50 + i[0], 50 + i[1]), custom_text, fill=shadow_color, font=font)

            draw.text((50, 50), custom_text, fill=(255, 255, 255), font=font)
        except:
            # Если шрифт не найден, используем системный
            font = ImageFont.load_default()
            draw.text((50, 50), custom_text, fill=(255, 255, 255), font=font)

    cover_path = "cover.jpg"
    bg.save(cover_path)
    return cover_path


def process_image(image_path, output_size=(1080, 1920)):
    """Обрабатывает изображение с размытым фоном"""
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

    img = img.resize((width, height), Image.Resampling.LANCZOS)

    # Создаем размытый фон
    bg = img.copy()
    bg = bg.resize(output_size, Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))

    # Размещаем оригинальное изображение по центру
    position = (
        (target_width - new_width) // 2,
        (target_height - new_height) // 2
    )
    bg.paste(img, position)

    temp_path = f"temp_{os.path.basename(image_path)}"
    bg.save(temp_path)
    return temp_path


def apply_transition(clip1, clip2, transition_type):
    duration = TRANSITION_DURATION

    background = ColorClip(clip1.size, color=(150, 150, 150), duration=duration)

    # Если размеры клипов не совпадают, уменьшаем размер второго клипа

    if clip1.size != clip2.size:
        clip2 = clip2.resize(clip1.size)

    if transition_type == TransitionType.FADE:
        return CompositeVideoClip([
            clip1.set_duration(clip1.duration - duration / 2),
            background.set_duration(duration / 2),
            clip2.set_start(clip1.duration - duration).crossfadein(duration)
        ])

    elif transition_type == TransitionType.SLIDE_RIGHT:
        moving_clip = clip2.set_position(
            lambda t: (min(0, -clip2.w + int((t / duration) * clip2.w)), 'center'))
        return CompositeVideoClip([
            background.set_duration(duration),
            clip1.set_end(clip1.duration - duration),
            moving_clip.set_start(clip1.duration - duration)
        ])



    elif transition_type == TransitionType.SLIDE_DOWN:
        moving_clip = clip2.set_position(
            lambda t: ('center', min(0, -clip2.h + int((t / duration) * clip2.h))))
        return CompositeVideoClip([
            background.set_duration(duration),
            clip1.set_end(clip1.duration - duration),
            moving_clip.set_start(clip1.duration - duration)])

    # По умолчанию - плавное затухание
    return CompositeVideoClip([
        clip1.set_duration(clip1.duration - duration / 2),
        clip2.set_start(clip1.duration - duration).crossfadein(duration)
    ])


def create_video(images, audio_path, output_path=DEFAULT_OUTPUT, duration=DEFAULT_DURATION, fps=DEFAULT_FPS):
    # Выбираем тип перехода
    transition_type = select_transition_type()

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

    # Создаем клипы для каждого изображения
    clips = [ImageSequenceClip([img], durations=[duration]) for img in processed_images]

    # Применяем переходы между клипами
    final_clip = clips[0]
    for next_clip in clips[1:]:
        final_clip = apply_transition(final_clip, next_clip, transition_type)

    # Добавляем аудио
    if audio_path:
        audio_clip = AudioFileClip(audio_path)
        if audio_clip.duration < final_clip.duration:
            audio_clip = audio_clip.loop(duration=final_clip.duration)
        else:
            audio_clip = audio_clip.subclip(0, final_clip.duration)
        final_clip = final_clip.set_audio(audio_clip)

    # Сохраняем видео
    final_clip.write_videofile(
        output_path,

        fps=fps,
        codec='libx264',
        audio_codec='aac',
        threads=4,
        preset='fast'
    )

    # Удаляем временные файлы
    for img_path in processed_images:
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
                print("Аудиофайл не выбран.Видео будет без звука.")
        elif choice == "2": # Тестовые файлы
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


