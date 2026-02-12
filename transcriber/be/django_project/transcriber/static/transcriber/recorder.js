// Script for recorder interaction and audio processing, using lamejs

// Timer function
function formatTime(sec) {
    const minutes = Math.floor(sec / 60);
    const seconds = sec % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function getCSRFToken() {
    return document.cookie
        .split("; ")
        .find(row => row.startsWith("csrftoken="))
        ?.split("=")[1];
}

function fetchTranscription(url) {
    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
        },
        body: formData,
    }).then((response) => response.json()
    ).then((data) => {
        // Hide no transcription message
        const noTranscriptionMessage = document.getElementById('no-transcription-message');
        noTranscriptionMessage.style.display = 'none';
        // Get form elements
        const formContainer = document.getElementById('form-container');
        let form = document.getElementById('reformat');

        // Get alternative form id and change id if null
        // This is for when user creates a new recording while still shown previous transcript that had been edited
        if (form == null) {
            form = document.getElementById('reformat_edited');
            form.id = 'reformat';

            // Update form button to correct form id and name
            const submitButton = document.querySelector(
                'button[name="reformat_edited"]'
            );
            submitButton.setAttribute('form', 'reformat');
            submitButton.name = 'reformat';
        }

        const formElements = form.elements;

        // Fill empty form elements matching Django forms used
        formElements.filename.value = data.context.transcription.filename;
        formElements.transcript.value = data.context.transcription.transcript;

        // Fill SOAP format section
        const soapTextContainer = document.getElementById('soap-text-container');

        // CKEditor widget puts editable text inside the body of an <iframe>
        const iframe = soapTextContainer.querySelector('iframe');
        const iframeBody = iframe.contentDocument.body;
        iframeBody.innerHTML = data.context.transcription.formatted_text;

        // Change hidden form container display from hidden to visible
        if (formContainer) {
            formContainer.style.display = 'block';
        }

        // Hide modal
        closeModal();
    }).catch((error) => {
        console.error('Error:', error);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Recorder variables
    let audioContext;
    let micStream;
    let scriptProcessor;
    let mp3Encoder;
    let mp3Data = [];

    // LLM voice input variables
    let chatAudioContext;
    let chatMicStream;
    let chatScriptProcessor;
    let chatMp3Encoder;
    let chatMp3Data = [];

    // Recorder elements
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const audioPlayback = document.getElementById('audioPlayback');
    const downloadLink = document.getElementById('downloadLink');

    // LLM voice input  elements
    const voiceChatStartBtn = document.getElementById('voiceChatStartBtn');
    const voiceChatStopBtn = document.getElementById('voiceChatStopBtn');

    // Timer variables
    let timerInterval;
    let seconds = 0;

    // Hide download by default
    downloadLink.style.display = 'none';

    // Get timezone offset
    const timezoneOffset = new Date().getTimezoneOffset();
    // Add local timezone offset to hidden form input
    const timezoneOffsetInput = document.getElementById('timezone_offset');
    // Flip sign because Python uses positive for ahead of UTC instead of negative
    timezoneOffsetInput.value = -(timezoneOffset);

    // Recorder buttons onclick actions
    startBtn.onclick = async () => {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const source = audioContext.createMediaStreamSource(micStream);
        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
        mp3Encoder = new lamejs.Mp3Encoder(1, audioContext.sampleRate, 128);
        mp3Data = [];

        scriptProcessor.onaudioprocess = function (event) {
            const input = event.inputBuffer.getChannelData(0);
            const int16 = floatTo16BitPCM(input);
            const mp3buf = mp3Encoder.encodeBuffer(int16);
            if (mp3buf.length > 0) { mp3Data.push(new Int8Array(mp3buf));
            }
        };

        source.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);
        startBtn.disabled = true;
        stopBtn.disabled = false;

        // Timer start
        seconds = 0;
        document.getElementById('timerDisplay').textContent = 'Recording: 00:00';
        timerInterval = setInterval(() => {
            seconds++;
            document.getElementById('timerDisplay').textContent = 'Recording: ' + formatTime(seconds);
        }, 1000);
    }

    stopBtn.onclick = () => {
        scriptProcessor.disconnect();
        micStream.getTracks().forEach(track => track.stop());
        const mp3buf = mp3Encoder.flush();

        if (mp3buf.length > 0) {
            mp3Data.push(new Int8Array(mp3buf));
        }

        const blob = new Blob(mp3Data, { type: 'audio/mp3' });
        const url = URL.createObjectURL(blob);

        audioPlayback.src = url;
        downloadLink.href = url;
        startBtn.disabled = false;
        stopBtn.disabled = true;

        // Get formatted local datetime string
        const currentDate = new Date();
        const year = currentDate.getFullYear();
        const month = String(currentDate.getMonth() + 1).padStart(2, '0');
        const day = String(currentDate.getDate()).padStart(2, '0');
        const hours = String(currentDate.getHours()).padStart(2, '0');
        const minutes = String(currentDate.getMinutes()).padStart(2, '0');
        const seconds = String(currentDate.getSeconds()).padStart(2, '0');

        // Combine into desired format: YYYYMMDD_HHMMSS
        const formattedDateTime = `${year}${month}${day}${hours}${minutes}${seconds}`;

        // Set download name to datetime string
        downloadLink.download = `${formattedDateTime}.mp3`;

        // Add local datetime to hidden form input as YYYYMMDDHHMMSS
        const hiddenInput = document.getElementById('local_datetime');
        hiddenInput.value = formattedDateTime;

        // Show download link
        downloadLink.style.display = 'block';

        // Stop timer
        clearInterval(timerInterval);
        const waitMessage = ' (Stopped)';
        document.getElementById('timerDisplay').innerHTML += waitMessage;

        // Create form data
        const formData = new FormData();
        formData.append('file', blob, `${formattedDateTime}.mp3`);
        formData.append('new_file', true);
        formData.append('local_datetime', formattedDateTime);
        formData.append('timezone_offset', timezoneOffset);

        // Show loading modal
        textModal('Please wait for transcription to complete...');

        // Send form data to server
        fetchTranscription(url, token)
    };


    // Voice chat buttons onclick actions
    voiceChatStartBtn.onclick = async () => {
        // Audio processing
        chatAudioContext = new (window.AudioContext || window.webkitAudioContext)();
        chatMicStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const source = chatAudioContext.createMediaStreamSource(chatMicStream);
        chatScriptProcessor = chatAudioContext.createScriptProcessor(4096, 1, 1);
        chatMp3Encoder = new lamejs.Mp3Encoder(1, chatAudioContext.sampleRate, 128);
        chatMp3Data = [];

        chatScriptProcessor.onaudioprocess = function (event) {
            const input = event.inputBuffer.getChannelData(0);
            const int16 = floatTo16BitPCM(input);
            const mp3buf = chatMp3Encoder.encodeBuffer(int16);
            if (mp3buf.length > 0) { chatMp3Data.push(new Int8Array(mp3buf));
            }
        };

        source.connect(chatScriptProcessor);
        chatScriptProcessor.connect(chatAudioContext.destination);

        // Button display/disable
        voiceChatStartBtn.disabled = true;
        voiceChatStartBtn.style.display = 'none';
        voiceChatStopBtn.disabled = false;
        voiceChatStopBtn.style.display = 'inline-flex';
    }

    voiceChatStopBtn.onclick = () => {
        chatScriptProcessor.disconnect();
        chatMicStream.getTracks().forEach(track => track.stop());
        const mp3buf = chatMp3Encoder.flush();

        if (mp3buf.length > 0) {
            chatMp3Data.push(new Int8Array(mp3buf));
        }

        const blob = new Blob(chatMp3Data, { type: 'audio/mp3' });
        const url = URL.createObjectURL(blob);

        voiceChatStartBtn.disabled = false;
        voiceChatStartBtn.style.display = 'inline-flex';
        voiceChatStopBtn.disabled = true;
        voiceChatStopBtn.style.display = 'none';

        // Create form data
        const formData = new FormData();
        formData.append('file', blob, `instruction_audio.mp3`);
        formData.append('instruction_audio', true);

        const chatForm = document.getElementById('edit_chat');

        // Show loading modal
        textModal('Please wait for voice instruction transcription to complete...');

        // Send form data to server
        fetch("{% url 'transcriber:api_basic_transcribe' %}", {
            method: 'POST',
            headers: {
                'X-CSRFToken': '{{ csrf_token }}',
            },
            body: formData,
        }).then((response) => response.json()
        ).then((data) => {
            // Get form elements
            const form = document.getElementById('edit_chat');

            // Append transcript to input field
            form.input.value += ` ${data.context.transcript}`;

            // Hide modal
            closeModal();
        }).catch((error) => {
            console.error('Error:', error);
        });
    };

    function floatTo16BitPCM(input) {
        const output = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return output;
    }

    // Get direct edit and LLM edit forms
    const editSoapForm = document.getElementById('edit_soap');
    const editSoapInstructForm = document.getElementById('edit_chat');

    // Get loading spinner overlay for the editor
    const loadingOverlay = document.getElementById('editor-spinner-overlay');

    // CKEditor widget puts editable text inside the body of an <iframe>
    // Use MutationObserver to detect when the iframe is loaded
    const observer = new MutationObserver((mutations) => {
        const iframe = document.querySelector('iframe');
        if (iframe) {
            observer.disconnect();

            // SOAP note direct edit handling
            function editSoapNote(form) {
                // Get the form element and create a FormData object
                const formData = new FormData(form);

                // Get reformat form filename field for POST URL from transcript form (2 different forms possible)
                const reformatForm = document.getElementById('reformat') || document.getElementById('reformat_edited');
                formData.append('filename', reformatForm.filename.value);
                
                // Add distinguishing key for direct edit form
                formData.append('edit_soap', true)

                // Display loading overlay to cover editor
                loadingOverlay.style.display = 'flex';

                // Send form data to server
                fetch("{% url 'transcriber:api_update_soap'%}", {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}',
                    },
                    body: formData,
                }).then(
                    response => response.json()
                ).then(data => {
                    console.log('Form submitted successfully:', data);
                    // No need to update as it should be the same as what is in the editor

                    // Hide loading overlay
                    loadingOverlay.style.display = 'none';
                }).catch(error => {
                    console.error('Error submitting form:', error);
                });
            }

            document.getElementById('edit_soap').addEventListener('submit', function(event) {
                // Alternative form submit action
                editSoapNote(editSoapForm);
            });


            // SOAP note LLM edit handling
            function editSoapNoteWithInstruction(form) {
                // Get the form element and create a FormData object
                const formData = new FormData(form);

                // Get reformat form filename field for POST URL from transcript form (2 different forms possible)
                const reformatForm = document.getElementById('reformat') || document.getElementById('reformat_edited');
                formData.append('filename', reformatForm.filename.value);
                
                // Add distinguishing key for direct edit form
                formData.append('edit_chat', true)
                
                // Display loading overlay to cover editor
                loadingOverlay.style.display = 'flex';

                // Send form data to server
                fetch("{% url 'transcriber:api_update_soap'%}", {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}',
                    },
                    body: formData,
                }).then(
                    response => response.json()
                ).then(data => {
                    console.log('Form submitted successfully:', data);
                    // Update iframe text editor
                    iframe.contentDocument.body.innerHTML = data.context.transcription.formatted_text;
                    // Clear instruction input
                    form.input.value = '';

                    // Hide loading overlay
                    loadingOverlay.style.display = 'none';
                }).catch(error => {
                    console.error('Error submitting form:', error);
                });
            }

            document.getElementById('edit_chat').addEventListener('submit', function(event) {
                // Alternative form submit action
                editSoapNoteWithInstruction(editSoapInstructForm);
            });
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    console.log('observer', observer);

    // Disable default form submit
    document.getElementById('edit_soap').addEventListener('submit', function(event) {
        // Prevent the default form submission
        event.preventDefault(); 
    });
    document.getElementById('edit_chat').addEventListener('submit', function(event) {
        // Prevent the default form submission
        event.preventDefault(); 
    });
});