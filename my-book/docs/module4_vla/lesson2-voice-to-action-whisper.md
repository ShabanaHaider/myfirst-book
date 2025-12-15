# Voice-to-Action (OpenAI Whisper)

## Overview
This lesson explains using OpenAI Whisper for voice commands. Whisper converts spoken commands into text that the robot can understand. The goal is to teach readers how to control robots via voice.

## Learning Objectives
By the end of this lesson, students will be able to:
- Set up and configure OpenAI Whisper for voice recognition
- Integrate Whisper with ROS 2 for real-time voice command processing
- Implement voice command validation and error handling
- Create robust voice-controlled robot interfaces

## Introduction to OpenAI Whisper

OpenAI Whisper is a state-of-the-art speech recognition model that can transcribe speech to text with high accuracy. It's particularly well-suited for robotics applications due to its robustness across different accents, background noises, and speaking styles.

### Why Whisper for Robotics?

Whisper offers several advantages for robotics applications:
- **High Accuracy**: Performs well across various audio conditions
- **Robustness**: Handles background noise and different accents effectively
- **Multilingual Support**: Works with multiple languages
- **Open Source**: Can be deployed locally without internet dependency
- **Real-time Capabilities**: Can process audio streams in near real-time

## Setting Up Whisper for Robotics

### Installation

First, install the required dependencies:

```bash
pip install openai-whisper
pip install speechrecognition
pip install pyaudio
```

For ROS 2 integration:

```bash
pip install rclpy
pip install std_msgs
```

### Basic Whisper Implementation

```python
import whisper
import torch
import numpy as np
import pyaudio
import wave
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class WhisperVoiceNode(Node):
    def __init__(self):
        super().__init__('whisper_voice_node')

        # Initialize Whisper model
        self.model = whisper.load_model("base")  # Choose: tiny, base, small, medium, large

        # Audio configuration
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.record_seconds = 5

        # Publisher for recognized commands
        self.command_publisher = self.create_publisher(String, 'voice_command', 10)

        # Start voice recognition
        self.audio = pyaudio.PyAudio()

        self.get_logger().info('Whisper Voice Recognition Node Started')

    def record_audio(self):
        """Record audio from microphone"""
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )

        self.get_logger().info('Recording...')
        frames = []

        for i in range(0, int(self.rate / self.chunk * self.record_seconds)):
            data = stream.read(self.chunk)
            frames.append(data)

        stream.stop_stream()
        stream.close()

        # Save to temporary WAV file for Whisper processing
        filename = "temp_recording.wav"
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        return filename

    def transcribe_audio(self, audio_file):
        """Transcribe audio file using Whisper"""
        result = self.model.transcribe(audio_file)
        return result["text"]

    def process_voice_command(self):
        """Main method to record and process voice commands"""
        try:
            # Record audio
            audio_file = self.record_audio()

            # Transcribe using Whisper
            transcription = self.transcribe_audio(audio_file)

            # Clean up temporary file
            import os
            os.remove(audio_file)

            # Log the transcription
            self.get_logger().info(f'Recognized: {transcription}')

            # Publish the recognized command
            msg = String()
            msg.data = transcription
            self.command_publisher.publish(msg)

            return transcription

        except Exception as e:
            self.get_logger().error(f'Error in voice processing: {e}')
            return None

def main(args=None):
    rclpy.init(args=args)
    voice_node = WhisperVoiceNode()

    # Create a timer to continuously listen for commands
    voice_node.create_timer(1.0, voice_node.process_voice_command)

    try:
        rclpy.spin(voice_node)
    except KeyboardInterrupt:
        voice_node.get_logger().info('Shutting down Whisper Voice Node')
    finally:
        voice_node.audio.terminate()
        voice_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

## Advanced Whisper Configuration

### Model Selection
Choose the appropriate Whisper model based on your needs:

- **tiny**: Fastest, least accurate (74M parameters)
- **base**: Good balance (146M parameters)
- **small**: Better accuracy (471M parameters)
- **medium**: High accuracy (769M parameters)
- **large**: Best accuracy (1550M parameters)

### Real-time Processing

For real-time applications, consider using streaming approaches:

```python
import queue
import threading

class StreamingWhisperNode(Node):
    def __init__(self):
        super().__init__('streaming_whisper_node')

        # Audio input queue
        self.audio_queue = queue.Queue()

        # Initialize model
        self.model = whisper.load_model("base")

        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_audio_stream)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream"""
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def process_audio_stream(self):
        """Process audio stream in background"""
        # Process audio chunks as they arrive
        while rclpy.ok():
            try:
                chunk = self.audio_queue.get(timeout=1.0)
                # Process chunk for voice activity detection
                # Only transcribe when speech is detected
            except queue.Empty:
                continue
```

## Integration with Robot Control

### Command Processing Pipeline

```python
class VoiceCommandProcessor:
    def __init__(self):
        self.command_keywords = {
            'move': ['go to', 'move to', 'navigate to', 'walk to'],
            'grasp': ['pick up', 'grasp', 'take', 'grab'],
            'speak': ['say', 'speak', 'tell me'],
            'stop': ['stop', 'halt', 'pause']
        }

    def parse_command(self, transcription):
        """Parse natural language command"""
        transcription_lower = transcription.lower()

        for action, keywords in self.command_keywords.items():
            for keyword in keywords:
                if keyword in transcription_lower:
                    # Extract parameters
                    remaining = transcription_lower.replace(keyword, '').strip()
                    return {
                        'action': action,
                        'parameters': remaining,
                        'confidence': self.calculate_confidence(transcription)
                    }

        return None

    def calculate_confidence(self, transcription):
        """Calculate confidence score for the transcription"""
        # Simple confidence based on length and common words
        words = transcription.split()
        if len(words) < 2:
            return 0.3  # Low confidence for very short transcriptions

        # In a real implementation, you'd use more sophisticated methods
        return 0.8  # Default high confidence for demo
```

## Error Handling and Robustness

### Voice Command Validation

```python
class VoiceCommandValidator:
    def __init__(self):
        self.valid_locations = ['kitchen', 'living room', 'bedroom', 'office', 'dining room']
        self.valid_objects = ['cup', 'book', 'phone', 'bottle', 'plate', 'remote']

    def validate_command(self, command):
        """Validate if the command is safe and executable"""
        if command['action'] == 'move':
            if command['parameters'] not in self.valid_locations:
                return False, f"Unknown location: {command['parameters']}"

        elif command['action'] == 'grasp':
            if command['parameters'] not in self.valid_objects:
                return False, f"Unknown object: {command['parameters']}"

        return True, "Command is valid"
```

## Performance Optimization

### Local Deployment
For privacy and performance, deploy Whisper models locally:

```python
# Download model once
model = whisper.load_model("base", download_root="./models")

# Use GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)
```

### Audio Preprocessing
Improve audio quality before Whisper processing:

```python
import scipy.signal
import numpy as np

def preprocess_audio(audio_data, sample_rate=44100):
    """Preprocess audio to improve recognition quality"""
    # Apply noise reduction
    # Normalize volume
    # Remove silence at beginning/end

    return audio_data
```

## Troubleshooting Common Issues

### Audio Input Problems
- Check microphone permissions
- Verify audio input levels
- Test with simple audio recording tools first

### Recognition Accuracy
- Ensure quiet environment
- Speak clearly and at consistent volume
- Use appropriate model size for your requirements

### Latency Issues
- Use smaller models for faster processing
- Implement voice activity detection to reduce unnecessary processing
- Consider edge computing solutions

## Summary

Voice-to-action using OpenAI Whisper enables natural human-robot interaction through speech. By properly configuring Whisper and integrating it with your robot's control system, you can create intuitive interfaces that allow users to control robots using natural language commands.

The key to success is balancing recognition accuracy with response time, implementing proper error handling, and ensuring the system operates safely in real-world environments.

In the next lesson, we'll explore how to connect voice commands to actual robot actions through cognitive planning.
