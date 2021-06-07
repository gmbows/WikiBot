import os,sys
import json,requests
import wikipediaapi
import plots
from datetime import date
from datetime import timedelta

def search_wiki(url):
  content = requests.get(url).content
  return json.loads(content)

class Article(object):
	def __init__(self,title):
		#Takes title in any form (spaces, lowercase, non-redirected)
		self.lang = "en"
		self.wiki_api = wikipediaapi.Wikipedia(self.lang)

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
		self.wiki_most_viewed_url = "https://en.wikipedia.org/w/api.php?action=query&generator=mostviewed&prop=pageviews&format=json"

		self.display_title = self.get_redirect(title)
		self.title = self.display_title
		self.init_page()
	
	def exists(self):
		return self.page.exists()

	def init_page(self):
		self.page = self.wiki_api.page(self.title)
		if(not self.page.exists()):
			self.title = self.title.replace(" ","_")
			self.page = self.wiki_api.page(self.title)
		if(not self.page.exists()):
			print("Unable to intialize page {0}".format(self.title))
			return

		self.url = self.page.fullurl
		self.links = self.page.links
		self.categories = self.page.categories
		self.sections = self.page.sections
		self.watchers = self.page.watchers


	def get_extract(self):
		sentence = (self.get_sentences(self.page.summary)[0])+"."
		blurb = self.page.summary[0:160]
		blurb = " ".join(blurb.split(" ")[0:-1])
		if(blurb[-1] == "."):
			blurb = blurb[:-1]
		blurb += "..."
		return (sentence if (len(sentence) > 100) else blurb)

	def normalize_pageviews(self,view_dict):
		for key in view_dict.keys():
			if(view_dict[key] == None):
				view_dict[key] = 0
		return view_dict

	def get_pageviews(self):
		content = json.loads(requests.get(self.wiki_pageviews_url.format(self.title)).content)
		try:
			pageid = content["query"]["pages"].keys()
			for id in pageid:
			 return self.normalize_pageviews(content["query"]["pages"][id]["pageviews"])
		except:
			return False

	def generate_pageview_chart(self):
		views = self.get_pageviews()
		xdata = [str(date.today()-timedelta(days=i))[6:] for i in range(0,len(views.keys())+1,10)]
		ydata = list(views.values())
		xdata.reverse()
		ctitle = "Last 60 day pageviews for article \"{0}\" ({1})".format(self.display_title,date.today())
		xlabel = "Day"
		ylabel = "Views"
		plots.create_bar_chart(ctitle,xlabel,ylabel,xdata,ydata)
	
	def get_cirrus_popularity(self):
		data = json.loads(requests.get(self.wiki_cirrus_url.format(self.title)).content)
		try:
			pageids = data["query"]["pages"].keys()
			for pageid in pageids:
				return data["query"]["pages"][pageid]["cirrusdoc"][0]["source"]["popularity_score"]
		except:
			return None

	def get_popularity(self):
		titles = self.get_links_to_titles()
		if(titles == False):
			return None

		backlinks = 0
		keys = self.page.links.keys()

		for _title in titles:
			if(_title not in keys):
				backlinks += 1

		return backlinks

	def get_links_to_titles(self):
		links_here = []
		cont = 0
		while(True):
			content = json.loads(requests.get(self.wiki_links_here_url.format(self.title,cont)).content)
			try:
				pageid = content["query"]["pages"].keys()
				for id in pageid:
					links_here.extend([entry["title"] for entry in content["query"]["pages"][id]["linkshere"]])
			except:
				print("Error fetching links to {0}".format(self.title))
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

	def get_thumbnail_alt(self):
		filename = None
		images = json.loads(requests.get(self.wiki_page_images_url.format(self.title)).content)
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
			print("Error fetching thumbnail for page {0}".format(self.title))
			return None
		return None

	def get_thumbnail(self):
		content = json.loads(requests.get(self.wiki_thumbnail_url.format(self.title)).content)
		try:
			pageid = content["query"]["pages"].keys()
			for id in pageid:
			 return content["query"]["pages"][id]["thumbnail"]["source"]
		except:
			return self.get_thumbnail_alt()
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
		#return text
		keys = sorted(links.keys(),key=len)
		keys.reverse()
		for link_text in keys:
			if(link_text.lower() in text.lower()):
				wiki_object = self.wiki_api.page(link_text.replace(" ","_"))
				if(not wiki_object.exists()):
					print("error",link_text)
					continue
				text = text.replace(" "+link_text," [{0}]({1})".format(link_text,wiki_object.fullurl),1)
				#text = text.replace(link_text.lower(),"[{0}]({1})".format(link_text.lower(),wiki_object.fullurl))
		return text

	def get_sentences(self,text):
		return text.split(". ")