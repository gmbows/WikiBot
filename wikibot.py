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
  
  def get_sections(self,wiki_object):
    return [section.title for section in wiki_object.sections]
  
  def get_section(self,wiki_object,section_name):
    for section in wiki_object.sections:
      if(section.title.lower().startswith(section_name.lower())):
        return section
    return None

  def get_section_text(self,section,level=0):
    text = ""
    level=0
    if(len(section.sections) == 0):
      return section.text[0:100]
    for subsection in section.sections:
      text+= ("*" * (level + 1)) + subsection.title+": "+ subsection.text[0:100]+"\n"
      text+=self.get_section_text(subsection, level + 1)
    return text

  def init_events(self):
    @self.client.event
    async def on_ready():
      print("{0} ready to receive commands".format(self.client.user))
      self.running = True

  def init_commands(self):
    @self.client.command(pass_context=True)
    async def search(ctx,title,*args):
      query = "url"
      if(len(args) > 0):
        query = args[0]

      title = self.get_article_title_from_token(title)
      wiki_object = self.wiki_api.page(title)

      if(query == "summary"):
        await ctx.send(wiki_object.summary[0:100])
      elif(query == "url"):
        await ctx.send(wiki_object.fullurl)
      elif(query == "sections"):
        text = []
        for section in wiki_object.sections:
          text.append(section.title)
        await ctx.send(", ".join(text))
      elif(query == "section"):
        try:
          section_query = args[1]
        except:
          await ctx.send("> Usage: `!search [query] section [section]`")
        section = self.get_section(wiki_object,section_query)
        if(section != None):
          await ctx.send(self.get_section_text(section))
        else:
          await ctx.send("> Error: Section {0} not found\n> Use `!search [query] sections` for a list of sections".format(section_query))

      elif(query == "categories"):
        text = []
        for category in sorted(wiki_object.categories.keys()):
          text.append(category)
        await ctx.send("\n".join(text))