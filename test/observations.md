# Observations
A few OpenAI models and models found on HuggingFace are tested.
Local model transcription using faster-whisper is CPU only, while local model summarization is done by loading models from HuggingFace onto a server API using LM Studio.

Device specifications for comparisons mentioned here:
- CPU: i9-14900HX
- GPU: RTX 4070 (Laptop) 8 GB
- RAM: 32 GB

## Transcription
Testing was done using personal recordings of generated sample transcripts, and generated text to speech audio.
The generated text-to-speech audio files are included in the samples folder.

Tested Models:
- gpt-4o-mini-transcribe
- faster-whisper-large-v3-turbo

The audio file is directly given to the Whisper model in whole, while gpt-4o-transcribe required splitting the audio file into smaller chunks to stay under file size limits and avoid cut-offs and in the response text.

Tests showed high accuracy during transcription for both models. Accuracy of both models appears similar.

As the Whisper model is used via a local server and purely using the CPU, the speed is a fair amount slower than using the GPT model via OpenAI API. 

For example, using the audio file with time of 4:46:
- gpt-4o-mini-transcribe: around 20 seconds
- faster-whisper-large-v3-turbo (CPU only): around

## Summarization and Editing
Tested Models:
- gpt-4o-mini
- medgemma-4b-it
- medgemma-1.5-4b-it
- gemma-3-4b
- ministral-3-3b

gpt-4o-mini, the MedGemma models, and gemma-3-4b are observed to handle summarization well. However, hallucination can occur, with chances of hallucination seeming to increase with shorter, less detailed transcripts. Adjusting the prompts to try to avoid it is not entirely successful. Hallucinating exact blood pressure and pulse measurements was observed on one occasion when using medgemma-1.5-4b-it for a transcript that did not have exact measurements.

The models tested sometimes had problems with including reasoning, quotation marks, unwanted formatting (such as Markdown syntax) or other extra text in their response, requiring changes to the process to use structured output. This issue can still occur when instructing edits with formatting. The model ministral-3-3b provided partial responses, though details that were included were still accurate to the transcript.


Comparison with 4:46 sample audio:
- gpt-4o-mini summarization: around 5 seconds
- medgemma-1.5-4b-it: around 40 seconds
- medgemma-4b-it: around 30 seconds
- gemma-3-4b: around 30 seconds
- ministral-3-3b: around 20 seconds (incomplete structured output response)

With GPU use, the local models used via LM Studio were more comparable to using the OpenAI API.
