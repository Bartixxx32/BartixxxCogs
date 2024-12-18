"""
MIT License

Copyright (c) 2024 Bartixxx

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from redbot.core import commands
from redbot.core.bot import Red
import requests
from requests.structures import CaseInsensitiveDict

class Music(commands.Cog):
    """A simple cog to fetch YouTube audio using the Cobalt Tools API."""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    async def yt(self, ctx: commands.Context, url: str):
        """Play a YouTube video audio using the Cobalt Tools API."""
        # Check if the user is connected to a voice channel
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel to use this command.")
            return

        api_url = "https://api.cobalt.tools/api/json"
        headers = CaseInsensitiveDict({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "NeedDL/1.1.0"
        })

        # Prepare the payload for the API request
        json_data = {
            "url": url,
            "vQuality": "max",
            "filenamePattern": "basic",
            "youtubeVideoCodec": "h264",
            "audioBitrate": "320",
            "isAudioOnly": 'true'  # Set true for audio-only processing
        }

        try:
            # Send the POST request to the Cobalt Tools API
            resp = requests.post(api_url, headers=headers, json=json_data)
            resp.raise_for_status()  # Raise an error for bad responses

            # Print the response content for debugging
            print(resp.text)

            # Check if the response contains the download URL
            response_data = resp.json()
            if response_data.get("status") == "stream":
                output_url = response_data.get("url")  # Get the URL directly from the response

                if output_url:
                    # If we got a valid URL, pass it to the existing audio cog
                    await ctx.invoke(self.bot.get_command("play"), query=output_url)
                else:
                    await ctx.send("Could not retrieve the audio URL from the API response.")
            else:
                await ctx.send("The API response did not indicate a stream status.")
        except requests.RequestException as e:
            # Log the full exception to the console for debugging
            print(f"Error while fetching audio URL: {e}")
            await ctx.send(f"An error occurred while trying to retrieve the audio: {str(e)}")

def setup(bot: Red):
    bot.add_cog(Music(bot))