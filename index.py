from pinecone import Pinecone
import os
from pytube import YouTube
from transcript import get_json_transcript
from indexer import index_video_transcript, search_videos
from dotenv import load_dotenv
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt

# Initialize rich console
console = Console()

# Load environment variables
load_dotenv()


def validate_youtube_url(url: str) -> bool:
    """
    Validate if the given URL is a valid YouTube video URL
    """
    try:
        if "youtube.com/watch?v=" not in url and "youtu.be/" not in url:
            return False

        # Try to extract video ID
        if "youtube.com/watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
        else:
            video_id = url.split("youtu.be/")[1].split("?")[0]

        return len(video_id) > 0
    except:
        return False


def process_video(url: str, index_name: str = None):
    """
    Process a YouTube video: get transcript and index it
    """
    try:
        # Get index name from environment variable or use default
        index_name = index_name or os.getenv("PINECONE_INDEX_NAME", "video-search")

        with console.status("[bold cyan]Processing video...") as status:
            status.update("[bold cyan]Extracting video ID...")
            # Handle both youtube.com and youtu.be URLs
            if "youtube.com/watch?v=" in url:
                video_id = url.split("watch?v=")[1].split("&")[0]
            else:
                video_id = url.split("youtu.be/")[1].split("?")[0]

            status.update("[bold cyan]Getting transcript...")
            transcript = get_json_transcript(video_id)

            if not transcript:
                raise ValueError(f"Could not get transcript for video {video_id}")

            status.update("[bold cyan]Indexing transcript...")
            index_video_transcript(video_id, transcript, index_name)

            console.print("[bold green]✓[/bold green] Video processed successfully")
            return video_id

    except Exception as e:
        console.print(f"[red]Error processing video: {str(e)}[/red]")
        raise


def search_transcript(query: str, top_k: int = 5):
    """
    Search through all indexed video transcripts
    """
    try:
        results = search_videos(query, top_k)
        return results
    except Exception as e:
        console.print(f"[red]Error searching transcript: {str(e)}[/red]")
        raise


def print_search_results(results: list):
    """
    Print search results in a nicely formatted table
    """
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    table = Table(title="Search Results", show_header=True, header_style="bold magenta")
    table.add_column("Video ID", style="cyan")
    table.add_column("Time Range", style="green")
    table.add_column("Text", style="white", no_wrap=False)
    table.add_column("Score", style="yellow")

    for result in results:
        table.add_row(
            result["video_id"],
            f"{result['start_formatted']} - {result['end_formatted']}",
            result["text"],
            f"{result['score']:.2f}",
        )

    console.print(table)


def print_menu():
    """
    Print the main menu
    """
    console.print(
        Panel.fit(
            "[bold blue]Main Menu[/bold blue]\n\n"
            "[white]1.[/white] Index a new YouTube video\n"
            "[white]2.[/white] Search through indexed videos\n"
            "[white]3.[/white] Exit",
            title="YouTube Video Transcript Indexer and Search",
        )
    )


def check_environment():
    """
    Check for required environment variables
    """
    if not os.getenv("GEMINI_API_KEY"):
        console.print(
            "[red]Error: GEMINI_API_KEY not found in environment variables[/red]"
        )
        console.print(
            "Please make sure you have set up your .env file with your Google API key"
        )
        return False

    if not os.getenv("PINECONE_API_KEY"):
        console.print(
            "[red]Error: PINECONE_API_KEY not found in environment variables[/red]"
        )
        console.print(
            "Please make sure you have set up your .env file with your Pinecone API key"
        )
        return False

    return True


def main():
    """
    Main application loop
    """
    try:
        if not check_environment():
            sys.exit(1)

        while True:
            console.clear()
            print_menu()

            choice = Prompt.ask(
                "Enter your choice", choices=["1", "2", "3"], default="1"
            )

            if choice == "1":
                # Index new video
                console.print("\n[bold]Index a New Video[/bold]")
                while True:
                    url = Prompt.ask(
                        "\nEnter YouTube video URL (or 'back' to return to menu)"
                    )

                    if url.lower() == "back":
                        break

                    if not validate_youtube_url(url):
                        console.print(
                            "[red]Invalid YouTube URL. Please try again.[/red]"
                        )
                        continue

                    try:
                        video_id = process_video(url)
                        console.print(
                            f"\n[green]Successfully indexed video:[/green] {video_id}"
                        )
                        Prompt.ask("\nPress Enter to continue")
                        break
                    except Exception as e:
                        console.print(f"\n[red]Failed to index video: {str(e)}[/red]")
                        if (
                            not Prompt.ask(
                                "\nWould you like to try another URL?",
                                choices=["y", "n"],
                                default="y",
                            )
                            == "y"
                        ):
                            break

            elif choice == "2":
                # Search videos
                console.print("\n[bold]Search Indexed Videos[/bold]")
                while True:
                    query = Prompt.ask(
                        "\nEnter your search query (or 'back' to return to menu)"
                    )

                    if query.lower() == "back":
                        break

                    top_k = IntPrompt.ask(
                        "How many results would you like to see?", default=5
                    )

                    try:
                        results = search_transcript(query, top_k)
                        print_search_results(results)

                        if (
                            not Prompt.ask(
                                "\nWould you like to search again?",
                                choices=["y", "n"],
                                default="y",
                            )
                            == "y"
                        ):
                            break
                    except Exception as e:
                        console.print(f"\n[red]Search failed: {str(e)}[/red]")
                        if (
                            not Prompt.ask(
                                "\nWould you like to try again?",
                                choices=["y", "n"],
                                default="y",
                            )
                            == "y"
                        ):
                            break

            else:  # choice == "3"
                console.print(
                    "\n[bold green]Thank you for using YouTube Video Transcript Indexer![/bold green]"
                )
                break

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Program terminated by user[/bold yellow]")
    except Exception as e:
        console.print(f"\n[red]An unexpected error occurred: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
