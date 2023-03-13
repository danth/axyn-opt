import asyncio
from contextlib import asynccontextmanager
import discord
import os
import tempfile


class Voice:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.connection = None
        self.timeout_task = None

    async def play(self, channel, source):
        async with self.use_in(channel) as connection:
            finished = asyncio.Event()
            connection.play(source, after=lambda _: finished.set())
            await finished.wait()

    @asynccontextmanager
    async def use_in(self, channel):
        async with self.lock:
            if self.timeout_task:
                self.timeout_task.cancel()

            if self.connection and self.connection.is_connected():
                if self.connection.channel != channel:
                    await self.connection.move_to(channel)
                    await channel.guild.change_voice_state(channel=channel, self_deaf=True)
            else:
                self.connection = await channel.connect(self_deaf=True)

            yield self.connection

            self.timeout_task = asyncio.create_task(self.timeout())

    async def timeout(self):
        await asyncio.sleep(120)

        async with self.lock:
            await self.connection.disconnect()


class VoiceManager:
    def __init__(self):
        self.voices = {}

    async def play_tts(self, channel, text):
        async with generate_tts(text) as source:
            await self.play(channel, source)

    async def play(self, channel, source):
        if channel.guild.id not in self.voices:
            self.voices[channel.guild.id] = Voice()

        await self.voices[channel.guild.id].play(channel, source)


@asynccontextmanager
async def generate_tts(text):
    (_, file) = tempfile.mkstemp(suffix=".wav")

    process = await asyncio.create_subprocess_exec(
        "mimic",
        "-t", text,
        "-o", file,
        "-voice", "slt_hts"
    )
    await process.wait()

    if process.returncode != 0:
        raise Exception("TTS failed")

    try:
        yield discord.FFmpegPCMAudio(file)
    finally:
        os.remove(file)
