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

import os
import aiohttp
import aiofiles
import yt_dlp
from urllib.parse import urlparse
from redbot.core import commands
import asyncio
from redbot.core import Config
import logging
import base64

class tttostr(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(
            streamable_email=None,
            streamable_password=None,
            enabled=False
        )

    @commands.command()
    @commands.is_owner()
    async def set_streamable_credentials(self, ctx, email: str, password: str):
        """
        Sets Streamble creds, OWNER ONLY
        """
        await self.config.streamable_email.set(email)
        await self.config.streamable_password.set(password)
        await ctx.send("Streamable credentials set successfully.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def toggle_video_uploader(self, ctx):
        """
        Toggle reuploads of tiktok videos on given guild
        """
        enabled = await self.config.enabled()
        await self.config.enabled.set(not enabled)
        if enabled:
            await ctx.send("Video uploader disabled.")
        else:
            await ctx.send("Video uploader enabled.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_enabled = await self.config.enabled()
        if guild_enabled:
            # Check if the message contains a TikTok URL
            if any(self.is_tiktok_url(url) for url in message.content.split()):
                # Download and upload the video
                await self.download_and_upload_video(message)

    async def download_and_upload_video(self, message):
        # Get the URL from the message content
        urls = [url for url in message.content.split() if self.is_tiktok_url(url)]

        for url in urls:
            # Download the video
            video_filename = await self.download_video(url)
            if video_filename:
                # Upload the video to Streamable
                upload_result = await self.upload_to_streamable(video_filename)
                if upload_result['success']:
                    # Wait for video processing to complete
                    await self.wait_for_video_processing(upload_result['video_url'], message.channel, message)
                else:
                    logging.error(f"Failed to upload video: {upload_result['error']}")
            else:
                logging.error("Failed to download video.")

    def is_tiktok_url(self, url):
        parsed_url = urlparse(url)
        return parsed_url.netloc.endswith('tiktok.com')

    async def download_video(self, url):
        try:
            # Set yt-dlp options for downloading the video
            ydl_opts = {
                'outtmpl': 'temp%(id)s.%(ext)s',  # Output file name template
            }
            # Create a yt-dlp object
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            # Download the video asynchronously
            result = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            video_filename = ydl.prepare_filename(result)
            logging.info("Video downloaded successfully.")
            return video_filename
        except Exception as e:
            logging.error(f"Error downloading video: {e}")
            return None

    async def upload_to_streamable(self, video_file):
        try:
            # Get Streamable credentials
            streamable_email = await self.config.streamable_email()
            streamable_password = await self.config.streamable_password()

            # Encode credentials as base64
            credentials = base64.b64encode(f"{streamable_email}:{streamable_password}".encode()).decode()
            
            # Set the authorization header
            headers = {"Authorization": f"Basic {credentials}"}

            # Get the full path of the video file
            full_path = os.path.abspath(video_file)

            # Open the video file
            async with aiofiles.open(full_path, 'rb') as file:
                file_content = await file.read()

                files = {'file': file_content}

                async with aiohttp.ClientSession() as session:
                    # Make a POST request to the Streamable API to upload the video
                    async with session.post('https://api.streamable.com/upload', data=files, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            video_url = f"https://streamable.com/{data['shortcode']}"
                            logging.info("Video uploaded to Streamable successfully.")
                            # Delete the temporary file
                            os.remove(full_path)
                            logging.info("Temporary file deleted.")
                            return {'success': True, 'video_url': video_url}
                        else:
                            error_message = await response.text()
                            logging.error(f"Error uploading to Streamable: {error_message}")
                            return {'success': False, 'error': error_message}
        except Exception as e:
            logging.error(f"Error uploading to Streamable: {e}")
            return {'success': False, 'error': str(e)}

    async def wait_for_video_processing(self, video_url, channel, message):
        try:
            # Extract shortcode from the video URL
            shortcode = video_url.split("/")[-1]
            # Check the status of the video periodically
            async with aiohttp.ClientSession() as session:
                while True:
                    # Make a GET request to the Streamable API to retrieve video information
                    async with session.get(f"https://api.streamable.com/videos/{shortcode}") as response:
                        if response.status == 200:
                            data = await response.json()
                            thumbnail_url = data.get('thumbnail_url')
                            if thumbnail_url:
                                # Thumbnail URL is present, video is ready
                                await channel.send(f"Video uploaded to Streamable: {video_url}", reference=message)
                                break
                            else:
                                # Video is still processing, wait for a few seconds before checking again
                                await asyncio.sleep(5)
                        else:
                            # Unable to retrieve video information, inform the user
                            await channel.send("Failed to retrieve video information from Streamable.", reference=message)
                            break
        except Exception as e:
            logging.error(f"Error waiting for video processing: {e}")
