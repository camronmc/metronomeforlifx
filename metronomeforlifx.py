# Latest edit April 15, 2019: bug fixes, added lpb
import requests
import time as t
import spotipy.util as util
import random
import yaml

global spotify_token, client_id, client_secret, lifx_token, colors, username, lpb, firstColor, spot_rate, config_file
colors = []
client_id = ""
client_secret = ""
lifx_token = ""
spotify_token = ""
username = ""
firstColor = "white"
lpb = 1
selector = "all"
scope = "user-read-currently-playing"
# number of seconds between API hits - default 5
spot_rate = 5
# custom config file to avoid committing secrets. 
config_file = 'metronomeconfig_cam.yml'


def main():
    datadict = get_variables()
    global client_secret, colors, client_id, lifx_token, username, lpb
    client_id = datadict["client_id"]
    client_secret = datadict["client_secret"]
    lifx_token = datadict["lifx_token"]
    username = datadict["spot_username"]
    colors = datadict["colors"]
    lpb = float(datadict["lpb"])
    brightness = datadict["lights_brightness"]
    selector = datadict["selector"]

    spotify_authenticate()

    # Set brightness
    params = {
        "brightness": brightness,
    }
    turn_on_results = requests.put('https://api.lifx.com/v1/lights/{}/state'.format(selector), params,
                                   auth=(lifx_token, ''))
    light_status(turn_on_results.json())

    play_song()


def play_song():
    global firstColor

    firstColor = colors[random.randint(0, (len(colors)-1))]
    colors.remove(firstColor)
    # try:
    secondColor = colors[random.randint(0, (len(colors)-1))]
    # except ValueError:
    #     secondColor = colors[0]
    colors.append(firstColor)
    print("First Color: " + firstColor + "; Second Color: " + secondColor)

    # Get data from currently playing song (bpm, id, and length)
    song_info = get_current_song()
    bpm = song_info[0]
    duration = song_info[1]  # in
    current_id = song_info[2]
    name = song_info[3]

    print("Track Title: " + str(name))
    print("Current Track ID: " + str(current_id))
    print("BPM: " + str(round(bpm, 2)))
    print("Lights Per Beat (can be changed in metronomeconfig.txt): " + str(lpb))

    # Get total beats in song, and time for period of pulse
    totalbeats = (duration / 60) * bpm
    time = ((duration / totalbeats) / lpb)
    print("Time Interval Per Light: " + str(round(time, 2)) + " seconds")  # Time for color to change

    # Make lights pulse to beat, have two colors change every beat
    data = {
        "color": str(firstColor),
        "period": (time * 2),
        "from_color": str(secondColor),
        "cycles": ((totalbeats / 2) * lpb),
        "power_on": "true",
        "persist": "true"
    }
    pulse = requests.post('https://api.lifx.com/v1/lights/{}/effects/pulse'.format(selector), data, auth=(lifx_token, ''))
    light_status(pulse.json())

    # poll every `spot_rate` seconds because no web hook exists
    print("Checking for a change in song every {} seconds...".format(spot_rate))
    print("Press CTRL-C to quit\n")

    while True:
        try:
            if get_song_id()[0] != current_id:
                play_song()
                break
            else:
                t.sleep(spot_rate)
        except KeyboardInterrupt:
            print(' Stopped')
            stop_lights(firstColor)
            break
        except TypeError:
            print('TypeError')
            play_song()


def stop_lights(color):
    params = {
        "color": str(color),
    }
    turn_on_results = requests.put('https://api.lifx.com/v1/lights/{}/state'.format(selector), params,
                                   auth=(lifx_token, ''))


def light_status(js):
    stat = js['results'][0]
    print("Light Status = " + stat['status'])
    if stat['status'] == 'offline':
        print("Sorry, your lights are offline")
        exit()


def get_song_id():
    header = {
        "Authorization": "Bearer {}".format(spotify_token)
    }
    get_id = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=header)
    try:
        song_content = get_id.json()
        id = song_content['item']['id']
        name = song_content['item']['name']
        return [id, name]
    except KeyError:
        spotify_authenticate()
        get_song_id()
    except TypeError:
        print("Spotify Error: make sure valid song is playing")
        exit()
    except ValueError: #TODO: see if this helps
        print("Error: looks like no song is playing")
        stop_lights(firstColor)
        exit()


def get_current_song():
    header = {
        "Authorization": "Bearer {}".format(spotify_token)
    }

    idandname = get_song_id()
    id = idandname[0]
    name = idandname[1]
    get_song = requests.get("https://api.spotify.com/v1/audio-analysis/{}".format(id), headers=header)
    song_info = get_song.json()
    print("spotify returns")
    print(song_info)
    tempo = song_info["track"]["tempo"]
    duration = song_info["track"]["duration"]
    return [tempo, duration, id, name]


def spotify_authenticate():
    global spotify_token
    token = util.prompt_for_user_token(username, scope, client_id, client_secret, "https://www.google.com/")
    if token:
        spotify_token = token
    else:
        print("Couldn't get proper Spotify authentication")
        exit()


def get_variables():
    dicti = {}
    with open(config_file, 'r') as file:
        dicti = yaml.safe_load(file)
    
    return dicti


if __name__ == "__main__":
    main()



