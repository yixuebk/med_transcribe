"""Test OpenAI Audio API transcription."""
import logging
import os
from openai import OpenAI
from pydantic import BaseModel
from pydub import AudioSegment
from pydub.silence import detect_silence
from faster_whisper import WhisperModel

from django_project.settings import OPENAI_API_KEY, LOCAL_LLM_API_PORT
from transcriber.models import Transcription


# Get logger
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)
local_client = OpenAI(
    api_key='',
    base_url=f'http://127.0.0.1:{LOCAL_LLM_API_PORT}/v1',
)

# OpenAI models
OPENAI_GPT_4O_MINI_TRANSCRIBE = "gpt-4o-mini-transcribe"

# Whisper model configuration
WHISPER_LARGE_V3_TURBO = "large-v3-turbo"
whisper_model = WhisperModel(WHISPER_LARGE_V3_TURBO, device="cpu", compute_type="int8")

STRUCTURED_OUTPUT_KEYS = 'Return JSON with the keys: subjective, objective, assessment, plan.'
VERBAL_TO_PROPER_NOTATION = ''.join([
    "Text may contain verbalizations of measurements, ",
    "so use proper written notations and units."
])

PROMPT_SUMMARIZATION = ''.join([
    "You are a medical assistant for summarizing patient encounters. ",
    "You expect a transcript of a doctor-patient conversation or related information. ",
    "If the user provides it, please summarize the transcript into a SOAP format note. ",
    "If it is not a valid transcript, leave the fields empty. ",
    "If there is insufficient information, do not make up information. ",
    "Do not make up any details not found in the transcript. ",
    "Use professional medical terminology. ",
    "Use basic HTML styling. Do not wrap in extra strings or quotations. ",
    "Translate to English if transcript is in another language.",
    STRUCTURED_OUTPUT_KEYS,
    VERBAL_TO_PROPER_NOTATION
])

PROMPT_EDIT = ''.join([
    "You are a medical assistant for editing encounter documentation.",
    "You will be given a SOAP format medical note and instructions on editing it. ",
    "Update the summary according to instructions.",
    "Use HTML styling consistent with the input, if formatting is requested. ",
    "Do not wrap in extra strings or quotations.",
    STRUCTURED_OUTPUT_KEYS,
    VERBAL_TO_PROPER_NOTATION
])

CHUNK_SIZE_MB = 35      # Actual stored file size around 3 MB when set to 35
MIN_SILENCE_LEN = 500   # Minimum silence to consider (ms)
SILENCE_THRESH = -40    # Silence threshold (dBFS)


class SOAPNote(BaseModel):
    """
    The SOAP format is as follows:
    - Subjective: The patient's subjective medical history.
    - Objective: The patient's objective medical history.
    - Assessment: The assessment of the patient.
    - Plan: The plan for the patient.
    """
    subjective: str
    objective: str
    assessment: str
    plan: str


    def __str__(self):
        """Output as a single string."""
        return '\n\n'.join([
            self.subjective,
            self.objective,
            self.assessment,
            self.plan
        ])

    def str_with_headers(self):
        """Output as a single string with headers."""
        return '\n\n'.join([
            f'Subjective:\n{self.subjective}',
            f'Objective:\n{self.objective}',
            f'Assessment:\n{self.assessment}',
            f'Plan:\n{self.plan}'
        ])

    def to_html(self):
        """Output as a single HTML string."""
        return '<br><br>'.join([
            self.subjective,
            self.objective,
            self.assessment,
            self.plan
        ])

    def to_html_with_headers(self):
        """Output as a single HTML string with headers."""
        return '<br><br>'.join([
            f'<b>Subjective:</b><br>{self.subjective}',
            f'<b>Objective:</b><br>{self.objective}',
            f'<b>Assessment:</b><br>{self.assessment}',
            f'<b>Plan:</b><br>{self.plan}',
        ])


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


def get_transcription_from_local_file(path: str, model_choice: str = WHISPER_LARGE_V3_TURBO):
    """Get transcription from OpenAI API."""
    transcripts = []
    logger.info('transcribing with model: %s', model_choice)

    if WHISPER_LARGE_V3_TURBO in model_choice:
        # Local whisper model transcription
        segments, info = whisper_model.transcribe(path, beam_size=5)
        logger.info(
            "Detected language '%s' with probability %s",
            info.language,
            info.language_probability
        )
        transcripts.append(' '.join(segment.text for segment in segments))
        logger.info('transcribed segments')
        logger.info(segments)
    else:
        # Split audio into chunks
        chunks = split_mp3_to_chunks(path, CHUNK_SIZE_MB)

        # Transcribe with OpenAI API transcription
        for idx, chunk_path in enumerate(chunks):
            logger.info("Transcribing chunk %s/%s: %s", idx + 1, len(chunks), chunk_path)

            # Transcribe chunk
            with open(chunk_path, "rb") as audio_file:
                try:
                    transcription = openai_client.audio.transcriptions.create(
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


def get_soap_format_from_transcription(transcript: str, model_choice: str):
    """Get SOAP format from transcription."""
    # Skip in case of empty transcript
    if not transcript.strip():
        return SOAPNote(
            subjective='n/a - no transcript text',
            objective='n/a - no transcript text',
            assessment='n/a - no transcript text',
            plan='n/a - no transcript text'
        ).to_html()

    logger.info('model_choice: %s', model_choice)

    messages = [
        {"role": "system", "content": PROMPT_SUMMARIZATION},
        {"role": "user", "content": transcript},
    ]

    if 'gpt' not in model_choice:
        # Get response from local OpenAI-like API
        response = local_client.chat.completions.parse(
            model=model_choice,
            response_format=SOAPNote,
            messages=messages
        )
    else:
        # Get response from OpenAI API
        response = openai_client.chat.completions.parse(
            model=model_choice,
            response_format=SOAPNote,
            messages=messages
        )

    parsed_output = response.choices[0].message.parsed

    return parsed_output.to_html_with_headers()


def update_soap_format_with_instruction(
    transcription_obj: Transcription,
    input_text: str,
    model_choice: str
):
    """Modify SOAP format with instruction."""
    messages = [
        {"role": "system", "content": PROMPT_EDIT},
        {"role": "user", "content": '\n'.join([
            'Text:',
            transcription_obj.formatted_text,
            'Instructions:',
            input_text
        ])},
    ]

    if 'gpt' not in model_choice:
        # Get response from local OpenAI-like API
        response = local_client.chat.completions.parse(
            model=model_choice,
            response_format=SOAPNote,
            messages=messages
        )
    else:
        # Get response from OpenAI API
        response = openai_client.chat.completions.parse(
            model=model_choice,
            response_format=SOAPNote,
            messages=messages
        )

    parsed_output = response.choices[0].message.parsed

    return parsed_output.to_html_with_headers()
