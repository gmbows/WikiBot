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

    self.base_wiki_url = "https://en.wikipedia.org/wiki/{0}" #title
    self.wiki_url = "https://en.wikipedia.org/w/api.php?action=opensearch&search={0}&limit=1&namespace=0&format=json"
    self.wiki_redirect_url = "https://en.wikipedia.org/w/api.php?action=query&format=json&titles={0}&redirects"
    self.wiki_thumbnail_url = "https://en.wikipedia.org/w/api.php?action=query&titles={0}&prop=pageimages&format=json&pithumbsize=300"
    self.wiki_page_images_url = "https://en.wikipedia.org/w/api.php?action=query&titles={0}&prop=images&format=json"
    self.wiki_fetch_image_data_url = "https://en.wikipedia.org/w/api.php?action=query&titles=Image:{0}&prop=imageinfo&iiprop=url&format=json" #.format(filename)
    self.wiki_category_url = "https://en.wikipedia.org/wiki/Category:{0}"

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

  def get_thumbnail_alt(self,title):
    filename = None
    images = json.loads(requests.get(self.wiki_page_images_url.format(title)).content)
    try:
      print("Test1")
      pageid = images["query"]["pages"].keys()
      for id in pageid:
       filename = images["query"]["pages"][id]["images"][0]["title"].replace("File:","")
       break
      print(filename)
      file_data = json.loads(requests.get(self.wiki_fetch_image_data_url.format(filename)).content)
      pageid = file_data["query"]["pages"].keys()
      for id in pageid:
        return file_data["query"]["pages"][id]["imageinfo"][0]["url"]
    except:
      print("Error")
      return None
    return None

  def get_thumbnail(self,title):
    title = self.get_redirect(title)
    content = json.loads(requests.get(self.wiki_thumbnail_url.format(title)).content)
    try:
      pageid = content["query"]["pages"].keys()
      for id in pageid:
       return content["query"]["pages"][id]["thumbnail"]["source"]
    except:
      return self.get_thumbnail_alt(title)
    return None

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

  def linkify(self,text,links):
    return text
    for link_text in sorted(links.keys()):
      if(link_text.lower() in text.lower()):
        wiki_object = self.wiki_api.page(self.get_article_title_from_token(link_text).replace(" ","_"))
        if(not wiki_object.exists()):
          print("error",link_text)
          continue
        text = text.replace(link_text,"[{0}]({1})".format(link_text,wiki_object.fullurl))
        text = text.replace(link_text.lower(),"[{0}]({1})".format(link_text.lower(),wiki_object.fullurl))
    return text

  def get_sentences(self,text):
    return text.split(". ")

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
        text = (self.get_sentences(wiki_object.summary)[0])+"."
        if("may refer to:" in text):
          cur_text = "This is a disambiguation page."
          embed_title = wiki_object.title+" (disambiguation)"
          embed = discord.Embed(title=embed_title,url=url, color=0xae99bd,type="rich")
          embed.add_field(name="Overview", value=cur_text,inline=False)
          #await ctx.send(None,embed=embed)
          text = []
          lastlevel = 0
          overflow = False
          header = "Related Pages"
          other = ["See also","Notes","References","Sources","External links"]
          article_url = wiki_object.fullurl
          total=len(cur_text)+len(embed_title)+50
          for key_name in sorted(wiki_object.links.keys()):
            if "Help:" in key_name or "Talk:" in key_name:
              continue
            temp_header = header
            newtext = "[{0}]({1})".format(key_name,self.base_wiki_url.format(key_name.replace(" ","_")))
            if(len(newtext)+total >= 6000):
              await ctx.send(None,embed=embed)
              embed.clear_fields()
              total=0
            if(len(newtext)+len("\n".join(text)) >= 1024):
              if(overflow):
                temp_header += " (cont.)"
              embed.add_field(name=temp_header, value="\n".join(text),inline=False)
              total+=1024
              overflow = True
              text=[newtext]
            else: 
              text.append(newtext)
          if(overflow):
            temp_header = header+" (cont.)"
          embed.add_field(name=temp_header, value="\n".join(text),inline=False)
          await ctx.send(None,embed=embed)
        else:
          #Non-disambiguation page
          embed = discord.Embed(title=wiki_object.title,url=url, color=0xae99bd,type="rich")
          thumb_url = self.get_thumbnail(wiki_object.title)
          if(thumb_url != None):
            embed.set_image(url=thumb_url)
          embed.add_field(name="Overview", value=text,inline=False)
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
        total=0
        embed = discord.Embed(title=wiki_object.title,url=article_url, color=0xae99bd,type="rich")
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
          if(len(newtext)+total >= 6000):
            await ctx.send(None,embed=embed)
            embed.clear_fields()
            total=0
          if(len(newtext)+len("\n".join(text)) >= 1024):
            if(overflow):
              temp_header += " (cont.)"
            embed.add_field(name=temp_header, value="\n".join(text),inline=False)
            total+=1024
            overflow = True
            text=[newtext]
          else: 
            text.append(newtext)
        embed.add_field(name=temp_header, value="\n".join(text),inline=False)
        await ctx.send(None,embed=embed)
      elif(query == "categories"):
        text = []
        lastlevel = 0
        overflow = False
        header = "Categories"
        article_url = wiki_object.fullurl
        total=0
        embed = discord.Embed(title=wiki_object.title,url=article_url, color=0xae99bd,type="rich")
        for section in sorted(wiki_object.categories.keys()):
          temp_header = header
          newtext = "[{0}]({1})".format(section.replace("Category:",""),self.wiki_category_url.format(section.replace("Category:","").replace(" ","_")))
          if(len(newtext)+total >= 6000):
            await ctx.send(None,embed=embed)
            embed.clear_fields()
            total=0
          if(len(newtext)+len("\n".join(text)) >= 1024):
            if(overflow):
              temp_header += " (cont.)"
            embed.add_field(name=temp_header, value="\n".join(text),inline=False)
            total+=1024
            overflow = True
            text=[newtext]
          else: 
            text.append(newtext)
        if(overflow):
          temp_header = header+ " (cont.)"
        embed.add_field(name=temp_header, value="\n".join(text),inline=False)
        await ctx.send(None,embed=embed)
      elif(query == "links"):
        text = []
        links = wiki_object.links
        for link_text in sorted(links.keys())[0:100]:
          text.append(str(link_text))
        await ctx.send("\n".join(text))
      else:
        section_query = query
        section = self.get_section(wiki_object,section_query)
        if(section != None):
          embed = discord.Embed(title=section.title+" ("+wiki_object.title+")",description=self.linkify(section.text[0:1024],wiki_object.links), color=0xEE8700,type="rich",url=wiki_object.fullurl+"#"+section.title.replace(" ","_"))
          await ctx.send(None,embed=embed)
        else:
          embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
          embed.add_field(name="Issue:", value="Section \"{0}\" not found in article [{1}]({2})".format(section_query,title,wiki_object.fullurl), inline=False)
          embed.add_field(name="Solution:", value="Use `!search \"{0}\" sections` for a list of sections in this article".format(title), inline=False)
          await ctx.send(None,embed=embed)