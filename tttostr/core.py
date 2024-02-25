import os
import requests
import yt_dlp
from urllib.parse import urlparse
from redbot.core import commands
import asyncio
from redbot.core import Config

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
        await self.config.streamable_email.set(email)
        await self.config.streamable_password.set(password)
        await ctx.send("Streamable credentials set successfully.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def toggle_video_uploader(self, ctx):
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
            video_filename = self.download_video(url)
            if video_filename:
                # Upload the video to Streamable
                video_url = await self.upload_to_streamable(video_filename)
                if video_url:
                    # Wait for video processing to complete
                    await self.wait_for_video_processing(video_url, message.channel, message)
                else:
                    await message.channel.send("Failed to upload video.")
            else:
                await message.channel.send("Failed to download video.")

    def is_tiktok_url(self, url):
        parsed_url = urlparse(url)
        return parsed_url.netloc.endswith('tiktok.com')

    def download_video(self, url):
        try:
            # Set yt-dlp options for downloading the video
            ydl_opts = {
                'outtmpl': 'temp%(id)s.%(ext)s',  # Output file name template
            }
            # Create a yt-dlp object
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download the video
                result = ydl.extract_info(url, download=True)
                video_filename = ydl.prepare_filename(result)
            print("Video downloaded successfully.")
            return video_filename
        except Exception as e:
            print("Error downloading video:", e)
            return None

    async def upload_to_streamable(self, video_file):
        try:
            # Open the video file
            with open(video_file, 'rb') as file:
                files = {'file': file}
                # Authenticate with Streamable
                auth = (await self.config.streamable_email(), await self.config.streamable_password())
                # Make a POST request to the Streamable API to upload the video
                response = requests.post('https://api.streamable.com/upload', files=files, auth=auth)
                if response.status_code == 200:
                    data = response.json()
                    video_url = f"https://streamable.com/{data['shortcode']}"
                    print("Video uploaded to Streamable successfully.")
                    # Delete the temporary file
                    os.remove(video_file)
                    print("Temporary file deleted.")
                    return video_url
                else:
                    print("Error uploading to Streamable:", response.text)
                    return None
        except Exception as e:
            print("Error uploading to Streamable:", e)
            return None

    async def wait_for_video_processing(self, video_url, channel, message):
        try:
            # Extract shortcode from the video URL
            shortcode = video_url.split("/")[-1]
            # Check the status of the video periodically
            while True:
                # Make a GET request to the Streamable API to retrieve video information
                response = requests.get(f"https://api.streamable.com/videos/{shortcode}")
                if response.status_code == 200:
                    data = response.json()
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
            print("Error waiting for video processing:", e)

def setup(bot):
    bot.add_cog(tttostr(bot))