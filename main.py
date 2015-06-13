#!/usr/bin/env python
from imgurpython import ImgurClient

import os
import argparse

# Google search imports
from bs4 import BeautifulSoup
from urlparse import urlparse, parse_qs
from random import choice as random_choice, randint
import requests

# Tagging imports
from PIL import Image, ImageDraw, ImageFont

# Twitterbot imports
cwd = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append(cwd + os.path.sep + os.path.pardir + os.path.sep + 'twitterbot')
import tb
os.chdir(cwd)

# Constants

CLIENT_ID = '42313947f8da0dd'
with file('client_secret') as f:
  CLIENT_SECRET = f.read()
LEFT_PADDING = 2
RIGHT_PADDING = 10
BOTTOM_PADDING = 20

# Set up ImgurClient
client = ImgurClient(CLIENT_ID, CLIENT_SECRET)

# Set up Twitter Client
TB = tb.Twitterbot()

def downloadImageForText(text):
  
  def buildUrl(searchText):
    # Some Cargo Culting going on here...here's what I've worked out
    # 
    # safe=off => SafeSearch off
    # tbs=... => options
    # isz:5mp => Larger than 5mp (http://bit.ly/1C4wKZI)
    # imgar:ns => Nearly-Square aspect ratio (http://googlesystem.blogspot.co.uk/2009/07/filter-images-by-aspect-ratio-and-size.html)
    url = 'https://www.google.co.uk/search?safe=off&hl=en&site=imghp&tbm=isch&source=hp&biw=1276&bih=675&gs_l=img.3..0j0i8i30l3j0i24l6.2607.4329.0.4456.11.11.0.0.0.0.125.753.7j2.9.0....0...1ac.1.64.img..2.9.751.nl6t0xvBQGg&tbs=isz:5mp,iar:ns'
    query = '+'.join(searchText.split())
    return url + '&q=' + query + '&oq=' + query

  def get_soup(url, headers):
    return BeautifulSoup(requests.get(url, headers=headers).text)

  def extractImageLinkFromGoogleLink(googleLink):
    # The magic "4" here is due to urlparse not providing named results: https://docs.python.org/2/library/urlparse.html
    # The final [0] is because queryString values are arrays
    return parse_qs(urlparse(googleLink)[4])['imgurl'][0]

  def downloadImageToPath(imageLink, path):
    r = requests.get(imageLink, stream = True)
    with file(path,'wb') as f:
      for chunk in r.iter_content(1024):
        f.write(chunk)

  soup = get_soup(buildUrl(text), {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.124 Safari/537.36'})

  googleLinks = [a.get('href') for a in soup.find_all('a') if a.get('href') is not None and 'imgurl' in a.get('href')]
  chosenLink = random_choice(googleLinks)
  imageLink = extractImageLinkFromGoogleLink(chosenLink)
  # If you want them all:
  # imageLinks = map(extractImageLinkFromGoogleLink, googleLinks)

  TEMPFILENAME = '/tmp/' + str(randint(100,200)) + '.jpg'
  downloadImageToPath(imageLink, TEMPFILENAME)
  return TEMPFILENAME

def tagImage(text, path):

  def buildFont(size):
    return ImageFont.truetype('/Library/fonts/Arial Rounded Bold.ttf', size)

  def addOutlinedText(coords, draw, text, size):
    font = buildFont(size)
    draw.text((coords[0], coords[1] + 1), text, (0,0,0), font=font)
    draw.text((coords[0] + 1, coords[1]), text, (0,0,0), font=font)
    draw.text((coords[0], coords[1] - 1), text, (0,0,0), font=font)
    draw.text((coords[0] - 1, coords[1]), text, (0,0,0), font=font)
    draw.text(coords, text, (255,255,255), font=font)

  def determineFontSize(draw, text, limit):
    firstEstimate = (200 * limit) / (133 * len(text))

    size = firstEstimate
    while (draw.textsize(text, buildFont(size))[0] > limit):
      size -= 10
    while (draw.textsize(text, buildFont(size))[0] < limit):
      size += 2
    return size

  image = Image.open(path)
  draw = ImageDraw.Draw(image)

  size = determineFontSize(draw, 'FUCK YEAH', image.size[0] - RIGHT_PADDING)
  addOutlinedText((LEFT_PADDING, 0), draw, 'FUCK YEAH', size)

  size = determineFontSize(draw, text, image.size[0] - RIGHT_PADDING)
  textHeight = draw.textsize(text, buildFont(size))[1]
  addOutlinedText((LEFT_PADDING,image.size[1] - textHeight - BOTTOM_PADDING), draw, text, size)

  updatedPath = path[:-4] + '_tagged' + path[-4:]
  image.save(updatedPath)
  return updatedPath

def uploadImageToImgur(path):
  return client.upload_from_path(path)['link']

def postText(text, prefix=None):
  text = text.upper()
  try:
    path = downloadImageForText(text)
    updatedPath = tagImage(text, path)
    url = uploadImageToImgur(updatedPath)
    tweetText = ('fuck yeah ' + text).upper() + ' ' + url + '.jpg'
    if prefix:
      tweetText = prefix + ' ' + tweetText
    TB.api.PostUpdate(tweetText)
  finally:
    try:
      os.remove(path)
    except Exception as e:
      pass
    try:
      os.remove(updatedPath)
    except Exception as e:
      pass

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--post', action='store_true', default=False)
  args = parser.parse_args()

  if args.post:
    config = random_choice([{'Pos1':'n','Level1':'35'}]*9 + [{'Pos1':'a','Level1':'35','Pos2':'n','Level2':'35'}])
    text = requests.post('http://watchout4snakes.com/wo4snakes/Random/RandomPhrase', config).text.upper()
    postText(text)
  else:
    with file('latestUpdate','r') as f:
      try:
        latestUpdate = int(f.read())
      except Exception:
        latestUpdate = 1

    mentions = TB.api.GetMentions(since_id=latestUpdate)

    with file('latestUpdate','w') as f:
      try:
        f.write(str(max(mentions, key=lambda x: x.id).id))
      except ValueError: #mentions is empty
        pass

    for mention in mentions:
      screen_name = mention.user.screen_name
      text = mention.text.replace('@FYeahNouns ','')
      if len(text) > 30:
        TB.api.PostUpdate('@' + screen_name + ' Can\'t handle that text, sorry!')
      else:
        postText(text, '@' + screen_name)
