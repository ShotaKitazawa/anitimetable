#!usr/bin/env python

from setuptools import setup, find_packages

setup(
        name            = "anitimetable",
	version         = "0.1",
	description     = 'Scraping "from http://cal.syoboi.jp/" and more',
        author          = "Shota Kitazawa"
        author_email    = "skitazawa1121@gmail.com"
	url             = "https://github.com/ShotaKitazawa/anitimetable",
        keywords        = "scraping anime program",
	packages        = find_packages(),
        install_requires= [beautifulsoup4, requests, tweepy,],
)
