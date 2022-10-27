# Imported Libraries
import re
import nltk
from nltk.corpus import stopwords
import wikipedia
from tqdm import tqdm
import warnings
from ratelimit import sleep_and_retry
import os

warnings.filterwarnings(
    "ignore"
)  # reason we are ignoring the warning is because we are using the wikipedia package to get the content of the articles but we don't mind if we miss a few along the way. As it is right now, the process is designed to be slightly imperfect.

# Global Variables Declaration ------------------------------------------------
# get the list of names from the topics file
nltk.download("stopwords")  # & download stopwords
stop_words = set(stopwords.words("english"))
maxlinksperpage = 30
minimum_key_occurrences = 4  # minimum number of times a keyword must appear in the text to be considered a keyword
context_config = {
    "prefix": "",
    "suffix": "\n",
    "tokenBudget": 100,  # max 2048
    "reservedTokens": 0,
    "budgetPriority": 400,
    "trimDirection": "trimBottom",
    "insertionType": "newline",
    "maximumTrimType": "sentence",
    "insertionPosition": -1,
}
master_dict = {} # get the list of keywords from the parent topic page.

#*###########################################################################################################
#& Functions
#*###########################################################################################################
#& Global Variables:
N = 10 # number of words each child page should have in common with the parent page to be considered.
#*############################################################################################################
#^ Getting the relevant subtopics for a parent topic (e.g. "Machine Learning" for "Artificial Intelligence"). This is done by getting the list of subtopics from the Wikipedia page of the parent topic and then getting the list of keywords (links) from the Wikipedia page of each subtopic. The subtopic is then considered relevant if it has at least N keywords in common with the parent topic.
##############################################################################################################

def filename_create(page_title):
    filename = page_title.replace(" ", "_") # replace spaces with underscores
    filename = filename.replace("/", "_") # replace slashes with underscores
    filename = filename.replace(":", "_") # replace colons with underscores
    filename = filename.replace("?", "_") # replace question marks with underscores
    filename = filename.replace("*", "_") # replace asterisks with underscores
    filename = filename.replace('"', "") # replace double quotes with underscores
    filename = filename.replace("'", "") # replace single quotes with underscores
    filename = filename.replace("<", "_") # replace less than signs with underscores
    filename = filename.replace(">", "_") # replace greater than signs with underscores
    filename = filename.replace("|", "_") # replace pipes with underscores
    filename = filename.replace("\\", "_") # replace backslashes with underscores
    filename = filename.replace("(", "_") # replace open parentheses with underscores
    filename = filename.replace(")", "_") # replace close parentheses with underscores
    filename = filename.replace("[", "_") # replace open brackets with underscores
    filename = filename.replace("]", "_") # replace close brackets with underscores
    filename = filename.replace("{", "_") # replace open braces with underscores
    filename = filename.replace("}", "_") # replace close braces with underscores
    filename = filename.replace(",", "_") # replace commas with underscores
    filename = filename.replace(".", "_") # replace periods with underscores
    filename = filename.replace(";", "_") # replace semicolons with underscores
    filename = filename.replace("=", "_") # replace equals signs with underscores
    filename = filename.replace("+", "_") # replace plus signs with underscores
    filename = filename.replace("-", "_") # replace minus signs with underscores
    filename = filename.replace("!", "_") # replace exclamation points with underscore
    filename = filename.replace("@", "_") # replace at signs with underscores
    filename = filename.replace("#", "_") # replace pound signs with underscores
    filename = filename.replace("$", "_") # replace dollar signs with underscores
    filename = filename.replace("%", "_") # replace percent signs with underscores
    filename = filename.replace("^", "_") # replace caret signs with underscores
    filename = filename.replace("&", "_") # replace ampersands with underscores
    filename = filename.replace("~", "_") # replace tildes with underscores
    filename = filename.replace("`", "_") # replace backticks with underscores
    filename = filename.replace("__","_") # replace double underscores with single underscores

    return filename # return the filename

def while_page_exists(page,filename):
    try:
        page_text = page.content # get the content of the page
        # save the page text to a file with the name of the page as the file name in the wikipedia_pages folder
        # to save storage space, we should parse the page_text and remove all extra spaces.
        page_text = re.sub(r"\s+", " ", page_text) # replace all extra spaces with a single space
        with open(f'wikipedia_pages/{filename}.txt', 'w+') as f:
            f.write(page_text)
        print(f'Saved {filename} to file.', end=' ')
        return True
    except:
        return False

@sleep_and_retry
def get_links(topic):
    # get all links from the topic page
    try:
        # filename
        filename = filename_create(topic)
        topic_page = wikipedia.page(topic)
        topic_links = topic_page.links
        #? While the page exists save the page text to a file with the name of the page as the file name in the wikipedia_pages folder
        while_page_exists(topic_page,filename)
    except Exception as e:
        topic_links = []

    return topic_links

def get_relevant_subtopics(parent_topic):
    # get the list of subtopics from the parent topic page.
    # get all links from the parent topic page

    # make sure that the topic page will show up in the search results
    parent_topic_links = get_links(parent_topic)
    #note: could use a for loop above until len(parent_topic_links) > 0

    # get the list of subtopics from the parent topic page.
    subtopics = []
    for link in tqdm(parent_topic_links):
        if ":" not in link:
            subtopics.append(link)

    # get the list of keywords from the parent topic page.
    parent_topic_keywords = get_links(parent_topic)

    # get the list of keywords from each subtopic page.
    subtopics_keywords = {}
    for subtopic in tqdm(subtopics):
        print(f'Getting keywords for {subtopic}...', end=' ')
        subtopics_keywords[subtopic] = get_links(subtopic)
        print(f'Found {len(subtopics_keywords[subtopic])}')

    # get the list of relevant subtopics
    relevant_subtopics = []
    for subtopic in subtopics_keywords:
        # get the number of keywords in common between the parent topic and the subtopic
        common_keywords = set(parent_topic_keywords).intersection(
            set(subtopics_keywords[subtopic])
        )
        if len(common_keywords) >= N:
            relevant_subtopics.append(subtopic)

    return relevant_subtopics

def divide_into_segments(page_file_content):
    # goal:
    # 1. divide the page into segments based on the pattern '== History ==' where History is the name of a section, and the page_name is the name of the dictionary entry.
    # 2. Save each segment to the dictionary entry for the page_name using the section name as the key.
    # 3. Return the dictionary entry for the page_name.
    # 4. If the page does not have any sections, then save the entire page as the value for the key 'content'.

    # get the list of sections
    sections = re.findall(r"==\s*(.*?)\s*==", page_file_content)
    # get the list of section contents
    section_contents = re.split(r"==\s*(.*?)\s*==", page_file_content)
    # remove the first element of the section_contents list because it is the content before the first section
    section_contents.pop(0)

    # create a dictionary entry for the page_name
    page_dictionary_entry = {}
    # if the page has sections
    if len(sections) > 0:
        # save each section content to the dictionary entry
        for i in range(len(sections)):
            page_dictionary_entry[sections[i]] = section_contents[i]
    # if the page does not have sections
    else:
        # save the entire page as the value for the key 'content'
        page_dictionary_entry["content"] = page_file_content

    return page_dictionary_entry

def add_to_master_dict(subdict):
    # given the results of divide_into_segments, add the subdict to the master dictionary
    # if the page_name is already in the master dictionary, then add the subdict to the existing dictionary entry
    # if the page_name is not in the master dictionary, then add the subdict as a new dictionary entry
    global master_dict
    for page_name in subdict:
        if page_name in master_dict:
            master_dict[page_name].update(subdict[page_name])
        else:
            master_dict[page_name] = subdict[page_name]

def clear_all_previously_saved_files():
    # delete all files in the wikipedia_pages folder
    for filename in os.listdir("wikipedia_pages"):
        os.remove(f"wikipedia_pages/{filename}")


def main():
    global N
    global master_dict

    print("\n\nWelcome to the Subtopic Finder!")
    print("This program will find subtopics for a given topic.")
    print("All subtopics will be saved (article text to the wikipedia_pages directory) and added to the master dictionary.")
    choice = input("\n  Would you like to clear previously generated articles? (y/n) ")
    if choice == "y":
        clear_all_previously_saved_files()

    print("Settings (Current):")
    print(f'N = {N} - The required minimum number of keywords in common between parent-child pages.')
    choice = input("Would you like to change settings? (y/n) ")
    if choice == "y":
        N = int(input("N = "))
        print(f'updated: N = {N}')

    print("Please wait while the program runs...")
    choice = input("Would you like to enter a topic (parent_page)? (y/n) ")
    if choice == "y":
        parent_page = input("Enter a topic: ")
    else:
        parent_page = "Nikola Tesla"
    relevant_subtopics = get_relevant_subtopics(parent_page)
    print(relevant_subtopics)

main()