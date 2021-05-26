import discord,os,sys,random,requests
from discord.ext import commands
import wikipediaapi
import json

def get_env_var(key):
  return os.environ[key]

def search_wiki(url):
  content = requests.get(url).content
  return json.loads(content)

class WikiBot(object):
  def __init__(self):

    self.wiki_url = "https://en.wikipedia.org/w/api.php?action=opensearch&search={0}&limit=1&namespace=0&format=json"
    self.wiki_api = wikipediaapi.Wikipedia('en')

    print("Creating new WikiBot object")
    self.running = False

    self.TOKEN = get_env_var("DISCORD_TOKEN")
    self.client = discord.ext.commands.Bot("!")

    self.init_commands()
    self.init_events()

    self.client.run(self.TOKEN)

  def get_json_from_token(self,token):
    url = self.wiki_url.format(token)
    return search_wiki(url)

  def get_article_url_from_token(self,token):
    json = self.get_json_from_token(token)
    return json[3][0]

  def get_article_title_from_token(self,token):
    json = self.get_json_from_token(token)
    return json[1][0]

  def init_events(self):
    @self.client.event
    async def on_ready():
      print("{0} ready to receive commands".format(self.client.user))
      self.running = True

  def init_commands(self):
    @self.client.command(pass_context=True)
    async def search(ctx,title):
      title = self.get_article_title_from_token(title)
      wiki_object = self.wiki_api.page(title)
      await ctx.send(wiki_object.summary[0:100])