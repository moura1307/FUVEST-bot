import discord
from discord.ext import tasks
from bs4 import BeautifulSoup
import requests
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
URL = "https://www.fuvest.br/enem-usp/"
THUMBNAIL_URL = "https://www.fuvest.br/wp-content/uploads/img-logo-fuvest.png"

# Set up Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@tasks.loop(hours=24)
async def fetch_news():
    try:
        channel = client.get_channel(CHANNEL_ID)
        if not channel:
            print(f"Error: Channel {CHANNEL_ID} not found!")
            return

        # Fetch webpage
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(URL, headers=headers)
        response.raise_for_status()

        # Parse articles
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all('article', class_="post")
        articles_data = []
        
        # Extract article data (newest first)
        for article in articles:
            try:
                title = article.find('h2', class_="elementor-post__title").text.strip()
                link = article.find('a')['href']
                articles_data.append({'title': title, 'link': link})
            except (AttributeError, TypeError):
                continue

        # Check last 15 messages for duplicates
        posted_urls = set()
        async for msg in channel.history(limit=15):
            # Check both embeds and plain text messages
            if msg.embeds:
                for embed in msg.embeds:
                    if embed.url:
                        posted_urls.add(embed.url)
            else:
                # Check for old-style plain text posts
                if msg.content and '\n' in msg.content:
                    url_line = msg.content.split('\n')[-1]
                    if url_line.startswith('http'):
                        posted_urls.add(url_line)

        # Reverse the list to process oldest first (post newest last)
        articles_data.reverse()

        # Post new articles with embeds and cooldown
        for article in articles_data:
            if article['link'] not in posted_urls:
                # Create embed
                embed = discord.Embed(
                    title=article['title'],
                    description="Clique na mensagem para abrir o link e ler a mais recente notícia da FUVEST! Em caso de erros contate o suporte!",
                    url=article['link'],
                    color=14356239  # Orange color
                )
                embed.set_thumbnail(url=THUMBNAIL_URL)
                
                # Send embed
                await channel.send(embed=embed)
                await asyncio.sleep(2)  # Prevent rate limiting

    except Exception as e:
        print(f"An error occurred: {e}")
        # Optionally notify the channel about errors
        # await channel.send(f"❌ Scraping failed: {str(e)}")

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    fetch_news.start()

client.run(TOKEN)