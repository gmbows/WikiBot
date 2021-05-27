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
    self.wiki_redirect_url = "https://en.wikipedia.org/w/api.php?action=query&format=json&titles={0}&redirects"
    self.wiki_thumbnail_url = "https://en.wikipedia.org/w/api.php?action=query&titles={0}&prop=pageimages&format=json&pithumbsize=300"

    self.wiki_api = wikipediaapi.Wikipedia('en')

    print("Creating new WikiBot object")
    self.running = False

    self.TOKEN = get_env_var("DISCORD_TOKEN")
    self.client = discord.ext.commands.Bot("!")

    self.init_commands()
    self.init_events()

    self.client.run(self.TOKEN)

  def get_redirect(self,title):
    content = json.loads(requests.get(self.wiki_redirect_url.format(title)).content)
    try:
      redirects = content["query"]["redirects"]
    except:
      return title
    return redirects[0]["to"]

  def get_thumbnail(self,title):
    title = self.get_redirect(title)
    content = json.loads(requests.get(self.wiki_thumbnail_url.format(title)).content)
    try:
      pageid = content["query"]["pages"].keys()
      for id in pageid:
       return content["query"]["pages"][id]["thumbnail"]["source"]
    except:
      return None
    return thumbnail_url

  def get_json_from_token(self,token):
    url = self.wiki_url.format(token)
    return search_wiki(url)

  def get_article_url_from_token(self,token):
    json = self.get_json_from_token(token)
    return json[3][0]

  def get_article_title_from_token(self,token):
    json = self.get_json_from_token(token)
    return json[1][0]
  
  def get_section_titles(self,wiki_sections,level=0):
    sections = []
    for section in wiki_sections:
      sections.append((level,section.title))
      sections.extend(self.get_section_titles(section.sections,level+1))
    return sections
  
  def get_section(self,wiki_object,section_name):
    for section in self.get_sections(wiki_object.sections):
      if(section.title.lower().startswith(section_name.lower())):
        return section
    return None

  def get_sections(self,wiki_sections):
    sections = []
    for section in wiki_sections:
      sections.append(section)
      sections.extend(self.get_sections(section.sections))
    return sections
	
  def get_section_text(self,section,level=0):
    text = "**" + section.title +"**"+ ": \n"+section.text[0:100]+"\n"
    level=0
    if(len(section.sections) == 0):
      return text
    for subsection in section.sections:
      text += self.get_section_text(subsection, level + 1)+"\n"
    return text 

  def init_events(self):
    @self.client.event
    async def on_ready():
      print("{0} ready to receive commands".format(self.client.user))
      self.running = True
    @self.client.event
    async def on_command_error(ctx,error):
      await ctx.send("> Error: "+str(error))

  def init_commands(self):
    @self.client.command(pass_context=True)
    async def search(ctx,title,*args):

      query = "overview"
      if(len(args) > 0):
        query = args[0]

      title = self.get_article_title_from_token(title)
      wiki_object = self.wiki_api.page(title)
      title = self.get_redirect(wiki_object.title)

      if(query == "summary"):
        await ctx.send(wiki_object.summary[0:100])
      elif(query == "overview"):
        url = wiki_object.fullurl
        embed = discord.Embed(title=wiki_object.title,url=url, color=0xdc143c,type="rich")
        url = self.get_thumbnail(wiki_object.title)
        if(url != None):
         embed.set_image(url=url)
        embed.add_field(name="Overview", value=wiki_object.summary[0:200],inline=False)
        await ctx.send(None,embed=embed)

      elif(query == "url"):
        await ctx.send(wiki_object.fullurl)
      elif(query == "sections"):
        text = []
        lastlevel = 0
        overflow = False
        header = "Sections"
        other = ["See also","Notes","References","Sources","External links"]
        article_url = wiki_object.fullurl
        embed = discord.Embed(title=wiki_object.title,url=article_url, color=0xdc143c,type="rich")
        for section in self.get_section_titles(wiki_object.sections):
          temp_header = header
          if(section[1] in other and "other" not in temp_header):
            if(overflow):
              temp_header += " (cont.)"
            embed.add_field(name=temp_header, value="\n".join(text),inline=False)
            text=[]
            header += " (other)"
          if(section[0] > lastlevel):
            newtext = ("     "*section[0])+"[{0}]({1})".format(section[1],article_url+"#"+section[1].replace(" ","_"))
          else:
            newtext = ("     "*section[0])+"[{0}]({1})".format(section[1],article_url+"#"+section[1].replace(" ","_"))
          lastlevel = section[0]
          if(len(newtext)+len("\n".join(text)) >= 1024):
            if(overflow):
              temp_header += " (cont.)"
            embed.add_field(name=temp_header, value="\n".join(text),inline=False)
            overflow = True
            text=[newtext]
          else: 
            text.append(newtext)
        embed.add_field(name=temp_header, value="\n".join(text),inline=False)
        await ctx.send(None,embed=embed)
      elif(query == "categories"):
        text = []
        for category in sorted(wiki_object.categories.keys())[0:20]:
          text.append(category[0:60])
        await ctx.send("\n".join(text))
      elif(query == "links"):
        text = []
        links = wiki_object.links
        for link_text in sorted(links.keys())[0:20]:
          text.append(str(link_text)+": "+str(links[link_text]))
        await ctx.send("\n".join(text))
      else:
        try:
          section_query = query
        except:
          await ctx.send("> Usage: `!search [query] section [section]`")
          return
        section = self.get_section(wiki_object,section_query)
        if(section != None):
          await ctx.send(self.get_section_text(section))
        else:
          embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
          embed.add_field(name="Issue:", value="Section \"{0}\" not found in article [{1}]({2})".format(section_query,title,wiki_object.fullurl), inline=False)
          embed.add_field(name="Solution:", value="Use `!search {0} sections` for a list of sections in this article".format(title), inline=False)
          await ctx.send(None,embed=embed)