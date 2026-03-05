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
- faster-whisper-large-v3-turbo (using [faster-whisper](https://pypi.org/project/faster-whisper/), which caches a compatible model on HuggingFace, either [mobiuslabsgmbh](https://huggingface.co/rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo) or [dropbox-dash](https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo), to the user's system)

The audio file is directly given to the Whisper model in whole, while gpt-4o-transcribe required splitting the audio file into smaller chunks to stay under file size limits and avoid cut-offs and in the response text.

Tests showed high accuracy during transcription for both models. Accuracy of both models appears similar.

As the Whisper model set to use only the CPU, the speed is a significantly slower than using the GPT transcription model via OpenAI API.

## Summarization and Editing
Tested Models:
- gpt-4o-mini
- medgemma-4b-it
- medgemma-1.5-4b-it
- gemma-3-4b
- ministral-3-3b

gpt-4o-mini, the MedGemma models, and gemma-3-4b are observed to handle summarization well. However, hallucination can occur, with chances of hallucination seeming to increase with shorter, less detailed transcripts. Adjusting the prompts to try to avoid it is not entirely successful. Hallucinating exact blood pressure and pulse measurements was observed on one occasion when using medgemma-1.5-4b-it for a transcript that did not have exact measurements. There is a similar possible issue of the model generating its own diagnosis or plans if none are provided in the transcript.

The models tested sometimes had problems with including internal reasoning dialogue, quotation marks, unwanted formatting (such as Markdown syntax) or other extra text in their responses, requiring changes to the process to use structured output. This issue can still occur when instructing edits with formatting. The model ministral-3-3b provided partial structured output responses, though details that were included were still accurate to the transcript.

Adding response format details ({"subjective":"Chief complaint, history of present illness, medical history, review of systems.", ...}) to the system prompt solved the issue of improper structured output (issue of unwanted styling remains), but made the other models more verbose than before. Providing only the JSON format keys ({"subjective":"","objective":"","assessment":"","plan":""}) in the prompt caused unexpected behavior in the MedGemma 1.5 and Gemma 3 models, with medgemma-1.5-4b-it providing an empty response, and gemma-3-4b-it becoming stuck in a runaway output generation. The unexpected behavior is repeated consistently on following generation attempts for the same transcript. Prompt changes were reverted and testing was not continued using ministral-3-3b.

The issue of medgemma-1.5-4b-it returning a empty responsse was also found in earlier testing with slightly different prompt versions. In all observed instances of this, the older medgemma-4b-it model was able to generate a proper response.

With GPU use, the generation times for the local models used via LM Studio were more similar to using the OpenAI API, but still slower.
