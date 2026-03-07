import machine, sndmixer, os
from esp32 import NVS

_no_channels = 4  # We can't play more than this number of channels concurrently without glitches
_started = False
handles = {}

def _start_audio_if_needed():
    global _started
    if not _started:
        sndmixer.begin(_no_channels)
        _started = True

def _clean_channel(channel_id):
    global handles
    if channel_id in handles:
        file = handles[channel_id]
        if file is not None:
            file.close()
        del handles[channel_id]

def _add_channel(filename, on_finished=None):
    global handles
    stream = True
    try:
        file = open(filename, 'rb')
    except:
        return -1
    lower = filename.lower()
    if(lower.endswith('.mp3')):
        channel_id = sndmixer.mp3_stream(file)
    elif(lower.endswith('.wav')):
        channel_id = sndmixer.wav_stream(file)
    elif(lower.endswith('.ogg') or
         lower.endswith('.opus')):
        channel_id = sndmixer.opus_stream(file)  # No support for looping yet
    elif(lower.endswith('.mod') or
         lower.endswith('.s3m') or
         lower.endswith('.xm')):
        channel_id = sndmixer.mod(file.read())  # No support for streaming mod files or looping yet
        stream = False
    else:
        print('Audio: unknown filetype')
        channel_id = -1

    if channel_id < 0:
        return -1

    def finish_callback(_):
        _clean_channel(channel_id)
        if on_finished is not None:
            try:
                on_finished()
            except:
                pass

    handles[channel_id] = file
    if stream:
        sndmixer.on_finished(channel_id, finish_callback)
    return channel_id

def play(filename, volume=None, loop=False, sync_beat=None, start_at_next=None, on_finished=None):
    if volume is None:
        try:
            volume = NVS('system').get_i32('volume') 
        except:
            volume = 255
    _start_audio_if_needed()
    channel_id = _add_channel(filename, on_finished)
    if channel_id is None or channel_id < 0:
        print('Failed to start audio channel')
        return channel_id
    sndmixer.volume(channel_id, volume)
    if loop:
        sndmixer.loop(channel_id, True)
    if sync_beat is not None and start_at_next is not None:
        sndmixer.start_beat_sync(sync_beat)
        sndmixer.start_at_next(channel_id, start_at_next)
    else:
        sndmixer.play(channel_id)
    return channel_id

def stop_channel(channel_id):
    _clean_channel(channel_id)
    sndmixer.stop(channel_id)

def stop_looping(channel_id):
    sndmixer.loop(channel_id, False)