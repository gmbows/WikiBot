import discord,os,sys,requests
from discord.ext import commands
import wikipediaapi
import json
import plots
from datetime import date
from datetime import timedelta

def get_env_var(key):
  return os.environ[key]

def search_wiki(url):
  content = requests.get(url).content
  return json.loads(content)

class WikiBot(object):
  def __init__(self):

    self.base_wiki_url = "https://en.wikipedia.org/wiki/{0}" #title
    self.wiki_search_url = "https://en.wikipedia.org/w/api.php?action=opensearch&search={0}&limit={1}&namespace=0&format=json"
    self.wiki_redirect_url = "https://en.wikipedia.org/w/api.php?action=query&format=json&titles={0}&redirects"
    self.wiki_thumbnail_url = "https://en.wikipedia.org/w/api.php?action=query&titles={0}&prop=pageimages&format=json&pithumbsize=800"
    self.wiki_page_images_url = "https://en.wikipedia.org/w/api.php?action=query&titles={0}&prop=images&format=json"
    self.wiki_fetch_image_data_url = "https://en.wikipedia.org/w/api.php?action=query&titles=Image:{0}&prop=imageinfo&iiprop=url&format=json"  #.format(filename)
    self.wiki_links_here_url = "https://en.wikipedia.org/w/api.php?action=query&prop=linkshere&titles={0}&format=json&lhprop=title&lhlimit=max&lhcontinue={1}&lhnamespace=0"
    self.wiki_category_url = "https://en.wikipedia.org/wiki/Category:{0}"
    self.wiki_pageviews_url = "https://en.wikipedia.org/w/api.php?action=query&titles={0}&prop=pageviews&format=json"
    self.wiki_external_links_url = "https://en.wikipedia.org/w/api.php?action=query&prop=extlinks&titles={0}"
    self.wiki_revisions_url = "https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles={0}&rvlimit=15&rvprop=timestamp|user|comment&format=json"
    self.wiki_random_url = "https://en.wikipedia.org/wiki/Special:Random"
    self.wiki_cirrus_url = "https://en.wikipedia.org/w/api.php?action=query&prop=cirrusdoc&titles={0}&format=json"

    self.wiki_api = wikipediaapi.Wikipedia('en')

    print("Creating new WikiBot object")
    self.running = False

    self.TOKEN = get_env_var("DISCORD_TOKEN")
    self.client = discord.ext.commands.Bot("!")

    self.init_commands()
    self.init_events()

    self.client.run(self.TOKEN)

  def normalize_pageviews(self,view_dict):
    for key in view_dict.keys():
      if(view_dict[key] == None):
        view_dict[key] = 0
    return view_dict

  def get_pageviews(self,title):
    title = self.get_redirect(title)
    content = json.loads(requests.get(self.wiki_pageviews_url.format(title)).content)
    try:
      pageid = content["query"]["pages"].keys()
      for id in pageid:
       return self.normalize_pageviews(content["query"]["pages"][id]["pageviews"])
    except:
      return False

  def generate_pageview_chart(self,title):
    views = self.get_pageviews(title)
    xdata = [str(date.today()-timedelta(days=i))[6:] for i in range(0,len(views.keys())+1,10)]
    ydata = list(views.values())
    xdata.reverse()
    ctitle = "Last 60 day pageviews for article \"{0}\" ({1})".format(title,date.today())
    xlabel = "Day"
    ylabel = "Views"
    plots.create_bar_chart(ctitle,xlabel,ylabel,xdata,ydata)
    


  def get_popularity(self,wiki_object):
    title = self.get_redirect(wiki_object.title)
    titles = self.get_links_to_titles(title)

    backlinks = 0
    keys = wiki_object.links.keys()

    for _title in titles:
      if(_title not in keys):
        backlinks += 1

    return backlinks

  def get_links_to_titles(self,title):
    links_here = []
    cont = 0
    while(True):
      content = json.loads(requests.get(self.wiki_links_here_url.format(title,cont)).content)
      try:
        pageid = content["query"]["pages"].keys()
        for id in pageid:
          links_here.extend([entry["title"] for entry in content["query"]["pages"][id]["linkshere"]])
      except:
        print("Error fetching links to {0}".format(title))
        return False

      if("continue" not in content.keys()):
        break
      cont = content["continue"]["lhcontinue"]

    return links_here



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
      pageid = images["query"]["pages"].keys()
      for id in pageid:
       filename = images["query"]["pages"][id]["images"][0]["title"].replace("File:","")
       break
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
    url = self.wiki_search_url.format(token,5)
    return search_wiki(url)

  def get_article_url_from_token(self,token):
    json = self.get_json_from_token(token)
    return json[3][0]

  def search_article_title_from_token(self,token,results):
    json = self.get_json_from_token(token)
    try:
      if(results == 0):
        try:
         return json[1][0]
        except:
          return False
      else:
        try:
         return json[1][0:results]
        except:
          return False
    except:
      return False
  
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
  
  def get_page_from_title(self,title):
    return self.base_wiki_url.format(title)

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

  async def paginate(self,ctx,wiki_object, header,text,desc=""):
    embed = discord.Embed(title=wiki_object.title,url=wiki_object.fullurl,description=desc, color=0xae99bd,type="rich")
    this_field = []
    overflow = False
    total=len(embed)
    ns = ["Category","Template talk","Wikipedia","Talk","Help","Portal","Template"]
    other = ["See also","Notes","References","External links"]

    longest = max([len(line.split("]")[0].split("[")[1]) for line in text])
    print(longest)
    if(longest < 30):
      in_line = True
    else:
      in_line = False
    
    for line in text:

      temp_header = header

      if 1 in [keyword+":" in line for keyword in ns]:
        continue

      if 1 in [keyword in line for keyword in other] and "other" not in temp_header:
        if(overflow):
          temp_header += " (cont.)"
        embed.add_field(name=temp_header, value="\n".join(this_field),inline=in_line)
        this_field=[]
        header += " (other)"

      temp_header = header
      if(len(line)+len("\n".join(this_field))+len(embed) >= 5500):
        await ctx.send(None,embed=embed)
        embed.clear_fields()
        total=0
      if(len(line)+len("\n".join(this_field)) >= 1024):
        if(overflow):
          temp_header += " (cont.)"
        try:
          embed.add_field(name=temp_header, value="\n".join(this_field),inline=in_line)
        except:
          print("ERROPR!")
        total+=1024
        overflow = True
        if(line[0] == ' '):
          line = " "+line[1:]
        this_field=[line]
      else: 
        this_field.append(line)
    if(overflow):
      temp_header = header+" (fin.)"
    embed.add_field(name=temp_header, value="\n".join(this_field),inline=True)
    await ctx.send(None,embed=embed)

  async def parse(self,ctx,wiki_object,query,args):
    title = self.get_redirect(wiki_object.title)
    if(title+" (disambiguation)" in wiki_object.links.keys()):
      print("DISAMBIGUABLE")
      #title += " (disambiguation)"
    text = (self.get_sentences(wiki_object.summary)[0])+"."
    if("may refer to:" in text):
      print("DISAMBIGUABLE")
      #title += " (disambiguation)"
    if(query == "summary"):
      await ctx.send(wiki_object.summary[0:100])
    elif(query == "overview"):
      url = wiki_object.fullurl
      text = (self.get_sentences(wiki_object.summary)[0])+"."
      if("may refer to:" in text or "may also refer to:" in text):
        #Disambiguation page
        await self.paginate(ctx,wiki_object, "Related Pages",["[{0}]({1})".format(key_name,self.base_wiki_url.format(key_name.replace(" ","_"))) for key_name in sorted(wiki_object.links.keys())])
        return
      else:
        #Non-disambiguation page
        text = (self.get_sentences(wiki_object.summary)[0])+"."
        embed = discord.Embed(title=wiki_object.title,url=url,description=text, color=0xae99bd,type="rich")
        thumb_url = self.get_thumbnail(wiki_object.title)
        if(thumb_url != None):
          embed.set_image(url=thumb_url)
        await ctx.send(None,embed=embed)
    elif(query == "url"):
      await ctx.send(wiki_object.fullurl)
    elif(query == "sections"):

      text = []
      article_url = wiki_object.fullurl

      for section in self.get_section_titles(wiki_object.sections):
        if(section[0] > 0):
          newtext = ("    "*section[0])+"└[{0}]({1})".format(section[1],article_url+"#"+section[1].replace(" ","_"))
        else:
          if(section[0] > 0):
            newtext = ("       "*section[0])+"[{0}]({1})".format(section[1],article_url+"#"+section[1].replace(" ","_"))
          else:
            newtext = ("     "*section[0])+"[{0}]({1})".format(section[1],article_url+"#"+section[1].replace(" ","_"))
        text.append(newtext)

      header = "Sections"
      await self.paginate(ctx,wiki_object, header,text)
    elif(query == "categories"):
      text = []

      for category in sorted(wiki_object.categories.keys()):
        newtext = "[{0}]({1})".format(category.replace("Category:",""),self.wiki_category_url.format(category.replace("Category:","").replace(" ","_")))
        text.append(newtext)

      header = "Categories"
      await self.paginate(ctx,wiki_object, header,text)
    elif(query == "links"):

      if(len(wiki_object.links.keys()) > 100):
        if(len(args) < 2 or args[1] != "conf"):
          text = "There are {1} links on this page. Running this command will send approximately {0} messages.".format(int(len(wiki_object.links.keys())/(18*3)),len(wiki_object.links.keys()))
          embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
          embed.add_field(name="Issue:", value=text, inline=False)
          embed.add_field(name="Solution:", value="Use `!search \"{0}\" links conf` to display them anyway.".format(title))
          await ctx.send(None,embed=embed)
          return

      text = []

      for key_name in sorted(wiki_object.links.keys()):
        newtext = "[{0}]({1})".format(key_name,self.base_wiki_url.format(key_name.replace(" ","_")))
        text.append(newtext)

      header = "Links"
      await self.paginate(ctx,wiki_object, header,text)
    elif(query == "linksto"):
      titles = self.get_links_to_titles(wiki_object.title)
      text = []

      for article_title in titles:
        newtext = "[{0}]({1})".format(article_title,self.base_wiki_url.format(article_title.replace(" ","_")))
        text.append(newtext)

      header = "Links here"
      await self.paginate(ctx,wiki_object, header,text)
    elif(query == "info"):
      embed = discord.Embed(title=title,url=wiki_object.fullurl, description=self.get_sentences(wiki_object.summary)[0]+".",color=0xae99bd,type="rich")
      thumb_url = self.get_thumbnail(wiki_object.title)
      if(thumb_url != None):
        embed.set_image(url=thumb_url)
      popularity = self.get_popularity(wiki_object)
      watchers = wiki_object.watchers
      views = self.get_pageviews(title)
      avg_views = sum(views.values())//len(views.values())
      self.generate_pageview_chart(title)
      file = discord.File("chart.png")

      embed.set_image(url="attachment://chart.png")
      embed.add_field(name="Popularity",value=popularity,inline=False)
      embed.add_field(name="Watchers",value=watchers,inline=False)
      embed.add_field(name="Sections",value=len(self.get_sections(wiki_object.sections)),inline=False)
      embed.add_field(name="Categories",value=len(wiki_object.categories),inline=False)
      embed.add_field(name="Links",value=len(wiki_object.links),inline=False)
      embed.add_field(name="Average daily pageviews / 60 days",value=avg_views,inline=False)

      await ctx.send(None,file=file,embed=embed)
    else:
      section_query = query
      section = self.get_section(wiki_object,section_query)
      if(section != None):
        embed = discord.Embed(title=section.title+" ("+wiki_object.title+")",description=self.linkify(section.text[0:1024],wiki_object.links), color=0xEE8700,type="rich",url=wiki_object.fullurl+"#"+section.title.replace(" ","_"))
        await ctx.send(None,embed=embed)
      else:
        embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
        embed.add_field(name="Query:", value="`!search {0} {1}`".format(title," ".join(args)), inline=False)
        embed.add_field(name="Issue:", value="Section \"{0}\" not found in article [{1}]({2})".format(section_query,title,wiki_object.fullurl), inline=False)
        embed.add_field(name="Solution:", value="Use `!search \"{0}\" sections` for a list of sections in this article".format(title), inline=False)
        await ctx.send(None,embed=embed)

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

      result_titles = self.search_article_title_from_token(title,5)

      feeling_lucky = 1 in [arg == "!" for arg in args]
      if(feeling_lucky and result_titles != False and len(result_titles) > 1):
        largs = list(args)
        largs.remove("!")
        args = tuple(largs)
        result_titles = [result_titles[0]]

      query = "overview"
      if(len(args) > 0):
        query = args[0]

      if(result_titles != False and len(result_titles) == 1):
        wiki_object = self.wiki_api.page(result_titles[0])
        await self.parse(ctx, wiki_object,query,args)
      elif(result_titles != False and len(result_titles) > 0):
        wiki_objects = [self.wiki_api.page(result_title) for result_title in result_titles]
        embed = discord.Embed(title="Top 5 results for: "+title, color=0xae99bd,type="rich")
        for obj in wiki_objects:
          embed.add_field(name=obj.title, value="[(Link)]({0}) ".format(obj.fullurl)+self.get_sentences(obj.summary)[0], inline=False)
        await ctx.send(None,embed=embed)
      else:
        embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
        embed.add_field(name="Query:", value="`!search {0} {1}`".format(title," ".join(args)), inline=False)
        embed.add_field(name="Issue:", value="A search for articles about \"{0}\" return 0 results".format(title), inline=False)
        embed.add_field(name="Solution:", value="Try a new search!", inline=False)
        await ctx.send(None,embed=embed)

    @self.client.command(pass_context=True)
    async def random(ctx):
      url = requests.get(self.wiki_random_url).url
      title = url.split("/")[-1]
      wiki_object = self.wiki_api.page(title.replace(" ","_"))
      text = (self.get_sentences(wiki_object.summary)[0])+"."
      embed = discord.Embed(title=wiki_object.title,url=url,description=text, color=0xae99bd,type="rich")
      thumb_url = self.get_thumbnail(wiki_object.title)
      if(thumb_url != None):
        embed.set_image(url=thumb_url)
      await ctx.send(None,embed=embed)

    @self.client.command(pass_context=True)
    async def getpage(ctx,title,*args):

      query = "overview"

      if(len(args) > 0):
        query = args[0]

      wiki_object = self.wiki_api.page(title)
      if(wiki_object.exists()):
        await self.parse(ctx, wiki_object,query,args)
      else:
        embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
        embed.add_field(name="Issue:", value="Article {0} not found".format(title), inline=False)
        embed.add_field(name="Solution:", value="Use `!search \"{0}\"` to search for articles with this title.".format(title), inline=False)
        await ctx.send(None,embed=embed)