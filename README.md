
# WikiBot

![image](https://raw.githubusercontent.com/gmbows/WikiBot/master/r2.PNG)

*Above: `!getpage replit info`*

WikiBot is a Discord bot built using Replit. WikiBot allows users to quickly and easily search for and display Wikipedia articles, and it provides access to most functionality in the WikiMedia API. In addition, users can
specify an article title and a section or heading, and WikiBot will send the section text to the server as an embed.

## Usage
WikiBot can be used in discussions to quickly display relevant information that users would otherwise have to find independently.
A basic search is performed by running the command `!search "article name"`.

## Parsing
A WikiBot command consists of two parts.  The selection of an article, and arguments that specify what information to display from or about the article.

An article can be acquired through several different commands:

* `!search "article name" !`: The ! character instructs WikiBot to select the top result from this query. If there are multiple results and a ! character is not present, an article will not be selected, and WikiBot will simply display the search results.

* `!getpage articlename`: Select an article directly.  Title will be normalized (removes punctuation characters and capitalizes) and redirected if applicable, but must otherwise be an exact match.

* `!random`: Select a random Wikipedia article.

Once an article is selected, additional arguments (see below) can be provided to specify what information to display.

## Arguments
Once an article has been selected (see above) users can provide additional arguments to instruct WikiBot what to display from or about the article:

*Note: If a non-named argument is provided after an article is acquried, WikiBot will assume this argument is a section title.*

#### Overview
`!getpage replit overview`: Select the [Replit](https://en.wikipedia.org/wiki/Replit) Wikipedia article, and provide a short summary.  This is the default argument if no other arguments are provided.

#### Sections (List)
`!getpage olm sections`: List the sections present in the [Olm](https://en.wikipedia.org/wiki/Olm) article.  Subsections will be formatted based on their level (section heading, subsection, sub-subsection, etc.). Section queries on section headings that have subsections but no text themselves will display a brief summary of each subsection.

#### Section (By name)
`!getpage olm etymology`: Display the [Etymology](https://en.wikipedia.org/wiki/Olm#Etymology) section from the [Olm](https://en.wikipedia.org/wiki/Olm) article. Section titles are autocompleted. An error is produced if the provided section is not present in the selected article (see note above).

#### Info
`!search replit ! info`: Search for token "replit", select the first result, and display information about the page, including a generic popularity score (the number of one-way [backlinks](https://en.wikipedia.org/wiki/Backlink) in the page), the number of watchers, links, categories, and sections, the article has, as well as the average pageviews over the last 60 days and a graph.

#### Categories
`!getpage mineral categories`: Display a list of categories that the [Mineral](https://en.wikipedia.org/wiki/Mineral) article is present in.

#### Links
`!random links`: Select an article at random, and display the links present in the article.

*Note: Due to the maximum embed size of 6000 characters, WikiBot will ask for confirmation if a command would require multiple messages to fit the full query result.* 

## Commands

#### Search
`!search frogs`: Display a list of the top 5 or fewer results for the query `frogs` in the Wikipedia search API.  If there is only one result, WikiBot will display the overview for this article unless additional arguments are present.

#### Getpage
`!getpage "richard stallman"`: Display an overview of the article [Richard Stallman](https://en.wikipedia.org/wiki/Richard_Stallman) unless additional arguments are present.

#### Random
`!random`: Display the overview of a [random Wikipedia article](https://en.wikipedia.org/wiki/Special:Random) unless additional arguments are present.

#### Top10
`!top10`: Display a list of the top 10 most viewed Wikipedia articles over the last 24 hours.

*Note: This API functionality is unreliable and may go down periodically throughout the day*

## Notes
### Disambiguation pages
Disambiguation pages may be acquired periodically through normal searches or getpage queries. To select a disambiguation page directly, users can simply try `!search "frog disambig" !` (note the ! character) and special formatting will be used to display the potential disambiguations.
