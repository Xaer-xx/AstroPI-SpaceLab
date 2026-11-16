#region text
"""
Pouzitie v tvojom main.py:
    print(teplota())
    foto("snimka.jpg")

Periferie:
  - Sense HAT: LED matica, teplota, vlhkost, tlak,
               orientacia, akcelerometer, gyroskop, kompas, senzor farby
  - Kamera (picamzero): foto, video
  - ISS (knižnica orbit): poloha, osvetlenie slnkom
"""
#endregion
import csv
from pathlib import Path
from time import sleep, time
from datetime import datetime, timezone

#list of processes
images = False
videos = False
tremorGraph = False

maxP = 42
start = True
numP = 1
numV = 1

# Cas startu programu (limit 9 a pol minuty = 570 s)
start_time = time()

# Priecinok skriptu
BASE_FOLDER = Path(__file__).parent.resolve()
data_file = BASE_FOLDER / "data_file.csv"

# Objekty sa vytvoria az pri prvom pouziti (lazy), aby import nepadol
_sense = None
_camera = None

#region FUNKCIE-PERIFERIE
def _get_sense():
    global _sense
    if _sense is None:
        from sense_hat import SenseHat
        _sense = SenseHat()
    return _sense


def _get_camera():
    global _camera
    if _camera is None:
        from picamzero import Camera
        _camera = Camera()
    return _camera


#region LED MATICA 8x8

def led_clear(color=(0, 0, 0)):
    """Zhasne celu maticu (alebo ju vyplni jednou farbou)."""
    _get_sense().clear(color)


def led_pixel(x, y, color):
    """Rozsvieti jeden pixel. x, y: 0-7, farba: (r, g, b) 0-255."""
    _get_sense().set_pixel(x, y, *color)


def led_pixels(colors):
    """Nastavi vsetkych 64 pixelov naraz. Zoznam 64 tuplov (r, g, b)."""
    _get_sense().set_pixels(colors)


def led_text(text, speed=0.1, color=(255, 255, 255), background=(0, 0, 0)):
    """Posuvny text na LED matici."""
    _get_sense().show_message(
        text, scroll_speed=speed, text_colour=color, back_colour=background
    )


def led_letter(letter, color=(255, 255, 255), background=(0, 0, 0)):
    """Zobrazi jedno pismeno."""
    _get_sense().show_letter(letter, text_colour=color, back_colour=background)


def led_rotate(angle):
    """Otoci zobrazenie: 0, 90, 180 alebo 270 stupnov."""
    _get_sense().set_rotation(angle)


def led_low_light(enable=True):
    """Znizi jas matice (vhodne pri fotkach v tme)."""
    _get_sense().low_light = enable
#endregion
#region ENVIRONMENTALNE SENZORY

def temperature():
    """Teplota v °C (zo senzora vlhkosti)."""
    return _get_sense().get_temperature()


def temperature_from_pressure():
    """Teplota v °C (zo senzora tlaku)."""
    return _get_sense().get_temperature_from_pressure()


def humidity():
    """Relativna vlhkost v %."""
    return _get_sense().get_humidity()


def pressure():
    """Tlak v milibaroch (hPa)."""
    return _get_sense().get_pressure()
#endregion
#region IMU (pohyb, orientacia)

def orientation():
    """Vrati dict {'pitch', 'roll', 'yaw'} v stupnoch."""
    return _get_sense().get_orientation()


def accelerometer():
    """Zrychlenie v g po osiach: dict {'x', 'y', 'z'}."""
    return _get_sense().get_accelerometer_raw()


def gyroscope():
    """Uhlova rychlost v rad/s po osiach: dict {'x', 'y', 'z'}."""
    return _get_sense().get_gyroscope_raw()


def compass():
    """Smer k magnetickemu severu v stupnoch (0-360)."""
    return _get_sense().get_compass()


def magnetometer():
    """Magneticke pole v mikrotesla po osiach: dict {'x', 'y', 'z'}."""
    return _get_sense().get_compass_raw()
#endregion
#region SENZOR FARBY A JASU (len Sense HAT v2)

def color_sensor():
    """Vrati (red, green, blue, clear) zo senzora farby. Len Sense HAT v2."""
    try:
        return tuple(_get_sense().colour.colour)
    except Exception as error:
        print(f"Color sensor not available: {error}")
        return None
#endregion
#region ISS (knižnica orbit)

def _get_iss():
    """Vrati objekt ISS. V simulatore je ISS funkcia, ktoru treba zavolat."""
    from orbit import ISS
    return ISS() if callable(ISS) else ISS


def iss_position():
    """Vrati (zemepisna_sirka, zemepisna_dlzka) ISS v stupnoch alebo None."""
    try:
        point = _get_iss().coordinates()
        return point.latitude.degrees, point.longitude.degrees
    except Exception as error:
        print(f"ISS position not available: {error}")
        return None


def iss_in_sunlight():
    """True ak je ISS prave osvetlena Slnkom, False ak je v tieni, None pri chybe."""
    try:
        try:
            from astro_pi_orbit import de421 as ephemeris
        except ImportError:
            try:
                from astro_pi_orbit import ephemeris
            except ImportError:
                from orbit import ephemeris
        from skyfield.api import load
        timescale = load.timescale()
        return bool(_get_iss().at(timescale.now()).is_sunlit(ephemeris))
    except Exception as error:
        print(f"ISS sunlight not available: {error}")
        return None
#endregion
#region ZAPIS DAT

def write_data(file_name):
    """Zapise jeden riadok nazbieranych dat do CSV (file_name = nazov fotky/videa)."""
    with open(data_file, "a", newline="") as file:
        csv.writer(file, lineterminator="\n").writerow([file_name, datetime.now(timezone.utc), temperature(), humidity(), pressure(), orientation(), accelerometer(), gyroscope(), compass(), iss_position(), iss_in_sunlight()])
#endregion
#region KAMERA

def image(name=None):
    global numP
    if numP > maxP:
        print("Image limit is full")
        return None
    if name is None:
        name = "image_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f") + ".jpg"
    path = BASE_FOLDER / name
    _get_camera().take_photo(str(path))
    numP += 1
    return name


def video(name=None, duration=5):
    """Nahra video (trvanie v sekundach) a pocas nahravania zapisuje data do CSV."""
    if name is None:
        name = "video_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f") + ".h264"
    path = BASE_FOLDER / name
    camera = _get_camera()
    try:
        camera.start_recording(str(path))
        video_start = time()
        row_name = name
        while time() - video_start < duration and time() - start_time < 570:
            write_data(row_name)
            row_name = ""
            sleep(1)
        camera.stop_recording()
    except Exception as error:
        print(f"Video error: {error}")
    return name


def camera_flip(vertical=False, horizontal=False):
    """Prevrati obraz kamery."""
    _get_camera().flip_camera(vflip=vertical, hflip=horizontal)
#endregion
#endregion

#region main
if __name__ == "__main__":
    if start == True:
        with open(data_file, "w", newline="") as file:
            file.write("file,time,temperature,humidity,pressure,orientation,accelerometer,gyroscope,compass,ISS-position,ISS-in-sunlight\n")
        start = False

    if images == False:
        for i in range(maxP):
            if time() - start_time > 570:
                break
            image_name = image()
            print("Image:", image_name)
            write_data(image_name)
        else:
            print("images DONE")
            images = True

    if videos == False and time() - start_time < 570:
        video()
        print("video DONE")
        videos = True


#endregion