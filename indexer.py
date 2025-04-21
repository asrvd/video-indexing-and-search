import google.generativeai as genai
import json
from typing import List, Dict
import os
from datetime import timedelta
from dotenv import load_dotenv
import sys
from tqdm import tqdm
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeRemainingColumn,
)

# Initialize rich console
console = Console()

# Load environment variables
load_dotenv()

# Get API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    console.print("[red]Error: GEMINI_API_KEY not found in environment variables[/red]")
    console.print(
        "Please make sure you have set up your .env file with your Google API key"
    )
    sys.exit(1)

try:
    # Configure Google AI with explicit API key
    with console.status("[bold green]Configuring Google AI..."):
        genai.configure(api_key=GEMINI_API_KEY, transport="rest")
    console.print("[bold green]✓[/bold green] Google AI configured successfully")
except Exception as e:
    console.print(f"[red]Error configuring Google AI: {str(e)}[/red]")
    sys.exit(1)


def create_chunks(transcript_data: List[Dict], chunk_size: int = 3) -> List[Dict]:
    """
    Create overlapping chunks from transcript data with metadata
    """
    chunks = []
    for i in range(0, len(transcript_data), chunk_size):
        chunk = transcript_data[i : i + chunk_size]

        # Combine text from chunks
        text = " ".join([entry["text"] for entry in chunk])

        # Store metadata
        start_time = chunk[0]["start"]
        end_time = chunk[-1]["start"] + chunk[-1]["duration"]

        chunks.append(
            {
                "text": text,
                "start_time": start_time,
                "end_time": end_time,
                "start_formatted": str(timedelta(seconds=int(start_time))),
                "end_formatted": str(timedelta(seconds=int(end_time))),
            }
        )

    return chunks


def get_embedding(text: str) -> List[float]:
    """
    Get embeddings for text using Google's Gemini
    """
    try:
        embedding_model = "models/embedding-001"
        embedding = genai.embed_content(
            model=embedding_model,
            content=text,
            task_type="retrieval_document",
            
        )
        return embedding["embedding"]
    except Exception as e:
        console.print(f"[red]Error getting embedding: {str(e)}[/red]")
        raise


def index_video_transcript(video_id: str, transcript_data: str, index_name: str = None):
    """
    Index a video's transcript chunks in Pinecone
    """
    from pinecone import Pinecone

    # Get index name from environment variable or use default
    index_name = index_name or os.getenv("PINECONE_INDEX_NAME", "video-search")

    # Get Pinecone API key
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY not found in environment variables")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            # Initialize Pinecone
            init_task = progress.add_task("[cyan]Initializing Pinecone...", total=1)
            pc = Pinecone(api_key=PINECONE_API_KEY)
            index = pc.Index(index_name)
            progress.update(init_task, advance=1)

            # Parse transcript data
            parse_task = progress.add_task("[cyan]Parsing transcript...", total=1)
            transcript = json.loads(transcript_data)
            progress.update(parse_task, advance=1)

            # Create chunks
            chunk_task = progress.add_task(
                "[cyan]Creating transcript chunks...", total=1
            )
            chunks = create_chunks(transcript)
            progress.update(chunk_task, advance=1)

            # Create and upsert embeddings
            embed_task = progress.add_task(
                "[cyan]Processing chunks...", total=len(chunks)
            )

            for i, chunk in enumerate(chunks):
                # Get embedding
                embedding = get_embedding(chunk["text"])

                # Create unique ID for each chunk
                chunk_id = f"{video_id}_chunk_{i}"

                # Upsert to Pinecone
                index.upsert(
                    vectors=[
                        {
                            "id": chunk_id,
                            "values": embedding,
                            "metadata": {
                                "video_id": video_id,
                                "text": chunk["text"],
                                "start_time": chunk["start_time"],
                                "end_time": chunk["end_time"],
                                "start_formatted": chunk["start_formatted"],
                                "end_formatted": chunk["end_formatted"],
                            },
                        }
                    ]
                )
                progress.update(embed_task, advance=1)

        console.print(
            "[bold green]✓[/bold green] Video transcript indexed successfully"
        )

    except Exception as e:
        console.print(f"[red]Error indexing video transcript: {str(e)}[/red]")
        raise


def search_videos(query: str, top_k: int = 5, index_name: str = None) -> List[Dict]:
    """
    Search through indexed video transcripts using natural language
    """
    from pinecone import Pinecone

    # Get index name from environment variable or use default
    index_name = index_name or os.getenv("PINECONE_INDEX_NAME", "video-search")

    # Get Pinecone API key
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY not found in environment variables")

    try:
        with console.status("[bold cyan]Searching videos...") as status:
            # Initialize Pinecone
            pc = Pinecone(api_key=PINECONE_API_KEY)
            index = pc.Index(index_name)

            # Get query embedding
            status.update("[bold cyan]Generating query embedding...")
            query_embedding = get_embedding(query)

            # Search in Pinecone
            status.update("[bold cyan]Searching through video transcripts...")
            results = index.query(
                vector=query_embedding, top_k=top_k, include_metadata=True
            )

            matches = [
                {
                    "video_id": match.metadata["video_id"],
                    "text": match.metadata["text"],
                    "start_time": match.metadata["start_time"],
                    "end_time": match.metadata["end_time"],
                    "start_formatted": match.metadata["start_formatted"],
                    "end_formatted": match.metadata["end_formatted"],
                    "score": match.score,
                }
                for match in results.matches
            ]

            console.print("[bold green]✓[/bold green] Search completed successfully")
            return matches

    except Exception as e:
        console.print(f"[red]Error searching videos: {str(e)}[/red]")
        raise
