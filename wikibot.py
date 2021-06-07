import discord,os,sys,requests
from discord.ext import commands
import wikipediaapi
import json
import plots
from datetime import date
from datetime import timedelta
from Article import Article

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
		self.wiki_fetch_image_data_url = "https://en.wikipedia.org/w/api.php?action=query&titles=Image:{0}&prop=imageinfo&iiprop=url&format=json"	#.format(filename)
		self.wiki_links_here_url = "https://en.wikipedia.org/w/api.php?action=query&prop=linkshere&titles={0}&format=json&lhprop=title&lhlimit=max&lhcontinue={1}&lhnamespace=0"
		self.wiki_category_url = "https://en.wikipedia.org/wiki/Category:{0}"
		self.wiki_pageviews_url = "https://en.wikipedia.org/w/api.php?action=query&titles={0}&prop=pageviews&format=json"
		self.wiki_external_links_url = "https://en.wikipedia.org/w/api.php?action=query&prop=extlinks&titles={0}"
		self.wiki_revisions_url = "https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles={0}&rvlimit=15&rvprop=timestamp|user|comment&format=json"
		self.wiki_random_url = "https://en.wikipedia.org/wiki/Special:Random"
		self.wiki_cirrus_url = "https://en.wikipedia.org/w/api.php?action=query&prop=cirrusdoc&titles={0}&format=json"
		self.wiki_most_viewed_url = "https://en.wikipedia.org/w/api.php?action=query&generator=mostviewed&prop=pageviews&format=json"

		self.wiki_api = wikipediaapi.Wikipedia('en')

		print("Creating new WikiBot object")
		self.running = False

		self.TOKEN = get_env_var("DISCORD_TOKEN")
		self.client = discord.ext.commands.Bot("!")

		self.init_commands()
		self.init_events()

		self.client.run(self.TOKEN)

	def get_extract(self,text):
		sentence = (self.get_sentences(text)[0])+"."
		blurb = text[0:160]
		blurb = " ".join(blurb.split(" ")[0:-1])
		if(blurb[-1] == "."):
			blurb = blurb[:-1]
		blurb += "..."
		return (sentence if (len(sentence) > 100) else blurb)

	def get_most_viewed_pages(self):
		#returns list of tuples (wiki_object,views) 
		rank = []
		content = json.loads(requests.get(self.wiki_most_viewed_url).content)
		try:
			pages = content["query"]["pages"]
		except:
			return None
		for pageid in pages.keys():
			tup = self.wiki_api.page(pages[pageid]["title"].replace(" ","_")),pages[pageid]["pageviews"][list(pages[pageid]["pageviews"].keys())[-1]]
			rank.append(tup)
		return rank


	
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
		text = [(level,section.title,section.text)]
		level=0
		for subsection in section.sections:
			#text.append((section.title,section.text))
			text.extend(self.get_section_text(subsection, level + 1))
		return text 
	
	def get_page_from_title(self,title):
		return self.base_wiki_url.format(title)

	def linkify(self,text,links):
		#return text
		keys = sorted(links.keys(),key=len)
		keys.reverse()
		for link_text in keys:
			if(link_text.lower() in text.lower()):
				wiki_object = self.wiki_api.page(link_text.replace(" ","_"))
				if(not wiki_object.exists()):
					print("error",link_text)
					continue
				text = text.replace(" "+link_text+" "," [{0}]({1}) ".format(link_text,wiki_object.fullurl),1)
				text = text.replace(" "+link_text+","," [{0}]({1}),".format(link_text,wiki_object.fullurl),1)
				text = text.replace(" "+link_text+"."," [{0}]({1}).".format(link_text,wiki_object.fullurl),1)
				text = text.replace(" "+link_text.lower()+"."," [{0}]({1}).".format(link_text.lower(),wiki_object.fullurl),1)
				text = text.replace(" "+link_text.lower()+","," [{0}]({1}),".format(link_text.lower(),wiki_object.fullurl),1)
				text = text.replace(" "+link_text.lower()+" "," [{0}]({1}) ".format(link_text.lower(),wiki_object.fullurl),1)
		return text

	def get_sentences(self,text):
		return text.split(". ")

	async def paginate(self,ctx,article, header,text,desc="",title=None,url=None,lines=True,heading=True):
		if(title == None):
			title = article.display_title
		if(url == None):
			url = article.url

		if not heading:
			header = "\u200b"

		embed = discord.Embed(title=title,url=url,description=desc, color=0xae99bd,type="rich")
		this_field = []
		overflow = False
		total=len(embed)
		ns = ["Category","Template talk","Wikipedia","Talk","Help","Portal","Template"]
		other = ["See also","Notes","References","External links","Footnotes"]

		try:
			longest = max([len(line.split("]")[0].split("[")[1]) for line in text])
		except:
			longest = 31

		if(longest < 30):
			in_line = True
		else:
			in_line = False

		if(lines==False):
			in_line = False
		reading_link = False
		link = []
		affixed = False
		for line in text:
			if line == "":
				continue
			line=line.replace("\n"," ")
			temp_header = header

			if 1 in [keyword+":" in line for keyword in ns]:
				continue

			if 1 in [keyword in line for keyword in other] and "other" not in temp_header:
				if(overflow and heading):
					temp_header += " (cont.)"
				if(len(this_field) > 0):
					if(lines):
						embed.add_field(name=temp_header, value="\n".join(this_field),inline=in_line)
					else:
						embed.add_field(name=temp_header, value=" ".join(this_field),inline=in_line)
					this_field=[]
				header += " (other)"

			temp_header = header
			if(not heading):
				temp_header = "\u200b"
			if(len(line)+len("\n".join(this_field))+len(embed) >= 5500):
				await ctx.send(None,embed=embed)
				embed.clear_fields()
				embed.description = ""
				total=0
			if(len(line)+len("\n".join(this_field)) >= 1023):
				if(overflow and heading):
					temp_header += " (cont.)"
				try:
					if(lines):
						if(not heading and embed.description == ""):
							embed.description = "\n".join(this_field)
						else:
							embed.add_field(name=temp_header, value="\n".join(this_field),inline=in_line)
							
						
					else:
						if reading_link:
							while(this_field[-1][0] != "["):
								link.insert(0,this_field[-1])
								this_field = this_field[0:-1]
							link.insert(0,this_field[-1])
							this_field = this_field[0:-1]
							if(not heading and embed.description == ""):
								embed.description = " ".join(this_field)
							else:
								embed.add_field(name=temp_header, value=" ".join(this_field),inline=in_line)
							affixed = True
						else:
							if(not heading and embed.description == ""):
								embed.description = " ".join(this_field)
							else:
								embed.add_field(name=temp_header, value=" ".join(this_field),inline=in_line)
				except:
					print("ERROPR!")
				total+=1024
				overflow = True
				if(line[0] == ' '):
					line = "\u200b"+line
				if affixed:
					this_field = []
					this_field.extend(link)
					this_field.append(line)
					link = []
					affixed = False
				else:
					this_field=[line]
			else: 
				this_field.append(line)
				if(line[0] == "["):
					reading_link = True
				if(line[-1] == ")" and reading_link):
					reading_link = False
		if(overflow and heading):
			temp_header = header+" (fin.)"
		if(len(this_field) > 0):
			if(lines):
				embed.add_field(name=temp_header, value="\n".join(this_field),inline=in_line)
			else:
				embed.add_field(name=temp_header, value=" ".join(this_field),inline=in_line)
		await ctx.send(None,embed=embed)

	async def parse(self,ctx,article,query,args):
		wiki_object = article.page
		if(article.title+" (disambiguation)" in article.links.keys()):
			print("DISAMBIGUABLE")
			#title += " (disambiguation)"
		text = article.get_extract()
		if("may refer to:" in text):
			print("DISAMBIGUABLE")
			#title += " (disambiguation)"
		if(query == "summary"):
			await ctx.send("Not implemented yet!")
		elif(query == "overview"):
			text = article.get_extract()
			if("may refer to:" in text or "may also refer to:" in text):
				#Disambiguation page
				await self.paginate(ctx,article, "Related Pages",["[{0}]({1})".format(key_name,self.base_wiki_url.format(key_name.replace(" ","_"))) for key_name in sorted(wiki_object.links.keys())])
				return
			else:
				#Non-disambiguation page
				text = article.get_extract()
				embed = discord.Embed(title=article.display_title,url=article.url,description=text, color=0xae99bd,type="rich")
				thumb_url = article.get_thumbnail()
				if(thumb_url != None):
					embed.set_image(url=thumb_url)
				await ctx.send(None,embed=embed)
		elif(query == "url"):
			await ctx.send(article.url)
		elif(query == "sections"):

			text = []
			article_url = article.url

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
			await self.paginate(ctx,article, header,text,article.get_extract())
		elif(query == "categories"):
			text = []

			for category in sorted(article.categories.keys()):
				newtext = "[{0}]({1})".format(category.replace("Category:",""),self.wiki_category_url.format(category.replace("Category:","").replace(" ","_")))
				text.append(newtext)

			header = "Categories"
			await self.paginate(ctx,article, header,text)
		elif(query == "links"):

			if(len(article.links.keys()) > 100):
				if(len(args) < 2 or args[1] != "conf"):
					text = "There are {1} links on this page. Running this command will send approximately {0} messages.".format(int(len(article.links.keys())/(18*3)),len(article.links.keys()))
					embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
					embed.add_field(name="Issue:", value=text, inline=False)
					embed.add_field(name="Solution:", value="Use `!search \"{0}\" links conf` to display them anyway.".format(article.title))
					await ctx.send(None,embed=embed)
					return

			text = []

			for key_name in sorted(article.links.keys()):
				newtext = "[{0}]({1})".format(key_name,self.base_wiki_url.format(key_name.replace(" ","_")))
				text.append(newtext)

			header = "Links"
			await self.paginate(ctx,article, header,text)
		elif(query == "linksto"):
			titles = article.get_links_to_titles()
			text = []

			for article_title in titles:
				newtext = "[{0}]({1})".format(article_title,self.base_wiki_url.format(article_title.replace(" ","_")))
				text.append(newtext)

			header = "Links here"
			await self.paginate(ctx,article, header,text)
		elif(query == "info"):
			embed = discord.Embed(title=article.display_title,url=article.url, description=article.get_extract(),color=0xae99bd,type="rich")
			thumb_url = article.get_thumbnail()
			if(thumb_url != None):
				embed.set_image(url=thumb_url)
			popularity = article.get_popularity()
			cpopularity = int(article.get_cirrus_popularity()*100000000)
			views = article.get_pageviews()
			avg_views = sum(views.values())//len(views.values())
			article.generate_pageview_chart()
			file = discord.File("chart.png")

			embed.set_image(url="attachment://chart.png")
			embed.add_field(name="Popularity",value=popularity,inline=True)
			embed.add_field(name="Popularity (CirrusSearch Score)",value=str(cpopularity)+" ([What is this?](https://www.mediawiki.org/wiki/Extension:CirrusSearch/Scoring#Rescoring))",inline=True)
			embed.add_field(name="Watchers",value=article.watchers,inline=False)
			embed.add_field(name="Sections",value=len(self.get_sections(article.sections)),inline=True)
			embed.add_field(name="Categories",value=len(article.categories),inline=True)
			embed.add_field(name="Links",value=len(article.links),inline=True)
			embed.add_field(name="Average daily pageviews / 60 days",value=avg_views,inline=False)

			await ctx.send(None,file=file,embed=embed)
			try:
				os.remove("chart.png")
			except:
				None

		else:
			section_query = query
			section = self.get_section(wiki_object,section_query)
			if(section != None):
				#embed = discord.Embed(title=section.title+" ("+wiki_object.title+")",description=self.linkify(section.text[0:1024],wiki_object.links), color=0xEE8700,type="rich",url=wiki_object.fullurl+"#"+section.title.replace(" ","_"))
				text = self.linkify(section.text,article.links).split(" ")
				if(text == [''] or len(text) == 0):
					titles = self.get_section_titles(section.sections)
					for title in titles:
						text.append("[{0}]({1}): {2}".format(title[1],article.url+"#"+title[1].replace(" ","_"),self.get_extract(self.get_section_text(self.get_section(wiki_object,title[1]))[0][2])))
						#print(self.get_section_text(self.get_section(wiki_object,title[1]))[0][2][0:100])
					header = section.title
					await self.paginate(ctx,article, header,text,desc="This section has the following subsections:",title=section.title+" ("+article.display_title+")",url=article.url+"#"+section.title.replace(" ","_"),lines=True,heading=False)
					return
				header = section.title
				await self.paginate(ctx,article, header,text,title=section.title+" ("+article.display_title+")",url=article.url+"#"+section.title.replace(" ","_"),lines=False,heading=False)
				#await ctx.send(None,embed=embed)
			else:
				embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
				embed.add_field(name="Query:", value="`!search \"{0}\" {1}`".format(article.title," ".join(args)), inline=False)
				embed.add_field(name="Issue:", value="Section \"{0}\" not found in article [{1}]({2})".format(section_query,article.title,wiki_object.fullurl), inline=False)
				embed.add_field(name="Solution:", value="Use `!search \"{0}\" sections` for a list of sections in this article".format(article.title), inline=False)
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
			if(feeling_lucky and result_titles != []):
				largs = list(args)
				largs.remove("!")
				args = tuple(largs)
				result_titles = [result_titles[0]]

			query = "overview"
			if(len(args) > 0):
				query = args[0]
			
			if(result_titles != False and len(result_titles) == 1):
				article = Article(result_titles[0])
				await self.parse(ctx, article,query,args)
			elif(result_titles != False and len(result_titles) > 0):
				articles = [Article(result_title) for result_title in result_titles]
				embed = discord.Embed(title="Top 5 results for: "+title, color=0xae99bd,type="rich")
				for article in articles:
					embed.add_field(name=article.title, value="[(Link)]({0}) ".format(article.url)+article.get_extract(), inline=False)
				await ctx.send(None,embed=embed)
			else:
				embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
				embed.add_field(name="Query:", value="`!search {0} {1}`".format(title," ".join(args)), inline=False)
				embed.add_field(name="Issue:", value="A search for articles about \"{0}\" return 0 results.".format(title), inline=False)
				embed.add_field(name="Solution:", value="Try a new search!", inline=False)
				await ctx.send(None,embed=embed)

		@self.client.command(pass_context=True)
		async def random(ctx,*args):
			url = requests.get(self.wiki_random_url).url
			title = url.split("/")[-1]
			article = Article(title.replace("_"," "))

			query = "overview"
			if(len(args) > 0):
				query = args[0]

			if not article.exists():
				print("Error fetching article {0}".format(url))
				embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
				embed.add_field(name="Issue:", value="Unable to display article [{0}]({1}) because its url is malformed or contains special characters.".format(article.title,url), inline=False)
				embed.add_field(name="Solution:", value="Try another article!", inline=False)
				await ctx.send(None,embed=embed)
				return
			await self.parse(ctx, article,query,args)

		@self.client.command(pass_context=True)
		async def getpage(ctx,title,*args):

			query = "overview"

			if(len(args) > 0):
				query = args[0]

			article = Article(title)
			if(article.exists()):
				await self.parse(ctx, article,query,args)
			else:
				embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
				embed.add_field(name="Issue:", value="Article \"{0}\" not found".format(title), inline=False)
				embed.add_field(name="Solution:", value="Use `!search \"{0}\"` to search for articles with this title.".format(title), inline=False)
				await ctx.send(None,embed=embed)
		@self.client.command(pass_context=True)
		async def top10(ctx):
			pages = self.get_most_viewed_pages()
			if(pages == None):
				embed = discord.Embed(title="Oh no!", color=0xEE8700,type="rich")
				embed.add_field(name="Issue:", value="Unable to fetch top 10 pages", inline=False)
				embed.add_field(name="Solution:", value="Try again later!", inline=False)
				await ctx.send(None,embed=embed)
				return
			embed = discord.Embed(title="Top 10 most viewed pages for {0}: ".format(date.today()), color=0xae99bd,type="rich")
			i=1
			invalid = 0
			for page in pages:
				if(not page[0].exists()):
					title = page[0].title
					if(title == "Special:Search"):
						title = "Wikipedia Search"
						desc = "This is the Wikipedia search page."
						url = "https://en.wikipedia.org/wiki/Special:Search"
						views = page[1]
						embed.add_field(name="{0} ({1} views)".format(title,views), value="{1}. [(Link)]({0}) ".format(url,i)+desc, inline=False)
					else:
						invalid+=1
					continue
				try:
					i+=1
					title = page[0].title
					article = Article(title)
					desc = article.get_extract()
					url = page[0].fullurl
					views = page[1]
				except:
					if(title == "Main Page"):
						desc = "This is the Wikipedia homepage."
						url = page[0].fullurl
						embed.add_field(name="{0} ({1} views)".format(title,views), value="{1}. [(Link)]({0}) ".format(url,i)+desc, inline=False)
					continue
				embed.add_field(name="{0} ({1} views)".format(title,views), value="{1}. [(Link)]({0}) ".format(url,i)+desc, inline=False)
			if(invalid > 0):
				embed.description = "Omitted {0} invalid or meta result(s).".format(invalid)
			await ctx.send(None,embed=embed)