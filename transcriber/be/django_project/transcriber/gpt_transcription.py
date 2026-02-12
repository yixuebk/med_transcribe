"""Test OpenAI Audio API transcription."""
import logging
import os
from openai import OpenAI
from pydub import AudioSegment
from pydub.silence import detect_silence

from django_project.settings import OPENAI_API_KEY


# Get logger
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

CHUNK_SIZE_MB = 35      # Actual stored file size around 3 MB when set to 35
MIN_SILENCE_LEN = 500   # Minimum silence to consider (ms)
SILENCE_THRESH = -40    # Silence threshold (dBFS)


def get_silence_split_points(audio, chunk_length):
    """Get silence split points from audio file."""
    audio_length = len(audio)
    # Detect silence sections
    silence_ranges = detect_silence(
        audio_segment=audio, min_silence_len=MIN_SILENCE_LEN, silence_thresh=SILENCE_THRESH
    )

    # Get center points of silence sections
    silence_range_midpoints = [(start + end) // 2 for start, end in silence_ranges]

    # Choose best split points near target chunk size
    split_points = [0]  # Always start at 0
    current_pos = 0

    while current_pos < audio_length:
        # Desired next point
        target_pos = current_pos + chunk_length
        logger.info("current_pos: %s, target_pos: %s", current_pos, target_pos)

        # Get points near target_pos but after current_pos
        candidates = []

        # If end of audio is greater than target_pos, choose silence candidates
        # Otherwise, just use audio length
        if target_pos < audio_length:
            for midpoint in silence_range_midpoints:
                # Min 10 seconds from current start and at most 10 seconds after target end
                if current_pos + 10000 < midpoint < target_pos + 10000:
                    candidates.append(midpoint)

        if not candidates:
            # No silence found in range, force split at target_pos or end
            split_point = min(target_pos, audio_length)
        else:
            # Pick silence point closest to target_pos
            split_point = min(candidates, key=lambda x: abs(x - target_pos))

        if split_point >= audio_length:
            break
        split_points.append(split_point)
        current_pos = split_point

    split_points.append(audio_length)  # Ensure final chunk

    return split_points


def split_mp3_to_chunks(mp3_path, chunk_size_mb):
    """Split an MP3 file into chunks. This function splits by silence points near the target chunk
    length, which is partially determined by average bytes per millisecond."""
    audio = AudioSegment.from_file(mp3_path)
    chunk_size_bytes = chunk_size_mb * 1024 * 1024

    # Estimate average bytes per millisecond
    total_bytes = len(audio.raw_data)
    duration_ms = len(audio)
    bytes_per_ms = total_bytes / duration_ms
    logger.info(
        "bytes_per_ms: %s, total_bytes: %s, duration_ms: %s",
        bytes_per_ms,
        total_bytes,
        duration_ms
    )

    # Calculate chunk duration in ms
    chunk_duration_ms = int(chunk_size_bytes / bytes_per_ms)

    logger.info("Getting silence split points...")
    split_points = get_silence_split_points(audio, chunk_duration_ms)

    # Split audio into chunks
    chunks = []
    for i in range(len(split_points) - 1):
        start = split_points[i]
        end = split_points[i + 1]
        logger.info("start: %s, end: %s", start, end)
        chunk = audio[start:end]
        chunk_path = f"chunk_{i:03d}.mp3"
        chunk.export(chunk_path, format="mp3")
        logger.info("Exported chunk_%03d.mp3 (%0.2fs)", i, (end - start)/1000)
        chunks.append(chunk_path)
    return chunks


def get_transcription_from_local_file(path):
    """Get transcription from OpenAI API."""
    chunks = split_mp3_to_chunks(path, CHUNK_SIZE_MB)

    transcripts = []
    for idx, chunk_path in enumerate(chunks):
        logger.info("Transcribing chunk %s/%s: %s", idx + 1, len(chunks), chunk_path)

        # Transcribe chunk
        with open(chunk_path, "rb") as audio_file:
            try:
                transcription = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio_file
                )
                transcripts.append(transcription.text)
            except Exception as e:
                logger.error("Error transcribing %s: %s", chunk_path, e)
                transcripts.append(f"[ERROR in chunk {chunk_path}]")
        # Remove chunk file after transcription
        os.remove(chunk_path)

    return "\n".join(transcripts)


def get_soap_format_from_transcription(transcript):
    """Get SOAP format from transcription."""
    # Set system prompt
    prompt = ''.join([
        "You are a medical transcriber. ",
        "You are given a transcript of a doctor-patient conversation. ",
        "Please summarize the transcript into a SOAP format note. ",
        "Use professional medical terminology. ",
        "Use basic HTML styling. Do not wrap in extra strings or quotations. ",
        "Translate to English if transcript is in another language. ",
        # "The SOAP format is as follows: ",
        # "S - Subjective: The patient's subjective medical history. ",
        # "O - Objective: The patient's objective medical history. ",
        # "A - Assessment: The patient's assessment. ",
        # "P - Plan: The patient's plan. ",
    ])

    # Get response from OpenAI API
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": transcript},
        ]
    )

    return response.choices[0].message.content

def update_soap_format_with_intruction(transcription_obj, input_text):
    """Modify SOAP format with instruction."""
    # Set system prompt
    prompt = ''.join([
        "You are a medical text editing assistant. ",
        "You will be given a SOAP format medical note and instructions on editing it. ",
        "Update and return the SOAP format note. Use HTML formatting. ",
    ])

    # Get response from OpenAI API
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": transcription_obj.formatted_text + '\n' + input_text},
        ]
    )

    return response.choices[0].message.content
