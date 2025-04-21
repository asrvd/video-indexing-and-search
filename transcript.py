from youtube_transcript_api import YouTubeTranscriptApi
import json


def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def format_transcript(transcript):
    if not transcript:
        return "No transcript available."

    formatted_text = ""
    for entry in transcript:
        text = entry["text"]
        start_time = entry["start"]
        duration = entry["duration"]

        # Format timestamp as MM:SS
        minutes = int(start_time // 60)
        seconds = int(start_time % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"

        formatted_text += f"[{timestamp}] {text}\n"

    return formatted_text

def get_json_transcript(video_id):
    transcript_data = get_transcript(video_id)
    json_transcript = json.dumps(transcript_data)
    
    return json_transcript


if __name__ == "__main__":
    # Example: Get transcript from a YouTube video
    video_id = "aYK0H85E_oU"  # Replace with your YouTube video ID

    transcript_data = get_transcript(video_id)
    formatted_transcript = format_transcript(transcript_data)

    print(formatted_transcript)

    #json format transcript
    json_transcript = json.dumps(transcript_data)
    with open("transcript.json", "w", encoding="utf-8") as file:
        file.write(json_transcript)


    # Optionally save to file
    with open("transcript.txt", "w", encoding="utf-8") as file:
        file.write(formatted_transcript)
