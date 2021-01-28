# Imports
import re
import csv
import requests
from collections import Counter
import sys
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from psaw import PushshiftAPI
from datetime import datetime, timedelta
import time
import argparse
import importlib
import urllib.request

get_tickers = importlib.import_module("get_tickers")
gt = get_tickers

subIndex = {
    "ASX_Bets": "http://www.asx.com.au/asx/research/ASXListedCompanies.csv",
    "wallstreetbets": "https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download"
}

api = PushshiftAPI()
parser = argparse.ArgumentParser()

def TendieHunter():
    # Arguments & Validation __________________________________________________ #

    parser.add_argument('--sub', help='The subreddit to target', default="ASX_Bets")
    parser.add_argument('--limitPerDay', help='The limit of submissions to process per day', default=250)
    parser.add_argument('--backDate', help='The amount of days back from today to process', default=30)
    parser.add_argument('--minRequiredMentions', help='The minimum required mentions on a given day to be plotted', default=1)

    args = parser.parse_args()

    SUBREDDIT, LIMITPERDAY, BACKDATE, MINREQMENTIONS = args.sub, args.limitPerDay, args.backDate, args.minRequiredMentions

    if not isinstance(SUBREDDIT, str):    
        SUBREDDIT = str(SUBREDDIT)

    if not isinstance(LIMITPERDAY, int):
        LIMITPERDAY = int(LIMITPERDAY)
    
    if not isinstance(BACKDATE, int):
        BACKDATE = int(BACKDATE)

    if not isinstance(MINREQMENTIONS, int):
        MINREQMENTIONS = int(MINREQMENTIONS)

    validSubreddits = ["ASX_Bets", "wallstreetbets"]

    if SUBREDDIT not in validSubreddits:
        error(SUBREDDIT + " is not a valid input value for --sub, please refer to the documentation for valid inputs")

    if LIMITPERDAY < 1 or LIMITPERDAY > 1000:
        error("--limitPerDay must be a value between 1 and 1000")

    if BACKDATE < 1 or BACKDATE > 180:
        error("--backDate must be a value between 1 and 180")

    if MINREQMENTIONS < 1 or MINREQMENTIONS > 10:
        error("--minRequiredMentions must be a value between 1 and 10")

    print("sub: " + SUBREDDIT)
    print("limitPerDay: " + str(LIMITPERDAY))
    print("backDate: " + str(BACKDATE))
    print("minRequiredMentions: " + str(MINREQMENTIONS))

    CSV_URL = subIndex[SUBREDDIT]

    # Import relevent ticker data ________________________________________________ #

    print("Requesting all current ticker symbols...")

    tickerStops = ["ASX"]
    validTickers = []
    stopCount = 0

    if SUBREDDIT == "wallstreetbets":
        tickers = gt.get_tickers(NYSE=True, NASDAQ=True, AMEX=True)
        if len(tickers) == 0:
            print("Could not get tickers for US markets right now, reverting to pre-loaded data")
            with open('tickers_us.csv', newline='') as us_tickers:
                reader = csv.reader(us_tickers, delimiter=',')
                for row in reader:
                    ticker = row[0]
                    try:
                        if ticker not in tickerStops: validTickers.append(ticker)
                    except:
                        stopCount += 1
        else:
            for ticker in tickers:
                try:
                    if ticker not in tickerStops: validTickers.append(ticker)
                except:
                    stopCount += 1

    elif SUBREDDIT == "ASX_Bets":

        response = urllib.request.urlopen(CSV_URL)
        print(response)
        lines = [l.decode('utf-8') for l in response.readlines()]
        reader = csv.reader(lines, delimiter=',')
        for row in reader:
            try:
                ticker = row[1]
                if ticker not in tickerStops:
                    validTickers.append(ticker)
            except:
                stopCount += 1

    print("Successfully retrieved " + str(len(validTickers)) + " tickers")

    # Iterate last x days ______________________________________________________ #

    print("Processing historical submissions for last " + str(BACKDATE) + " days on /r/" + SUBREDDIT + "...")

    printProgressBar(0, BACKDATE, prefix='Progress:', suffix='Complete', length=50)

    toAppend = []

    for i in range(BACKDATE):
        before = i
        if i == 0:
            before = int((datetime.now()).timestamp())
        else:
            before = str(i) + "d"
        
        psawList = api.search_submissions(
            before=before,
            subreddit=SUBREDDIT,
            filter=['url','author', 'title', 'subreddit'],
            limit=LIMITPERDAY,
            stop_condition=lambda x: 'bot' in x.author
        )

        refString = ""

        for sub in list(psawList):
            refString += " " + sub.title
        
        filteredTickers = []
        extractedTickers = re.findall(r'\b[A-Z]{3}\b', refString)
        for ticker in extractedTickers:
            if ticker in validTickers:
                filteredTickers.append(ticker)

        d = (datetime.now() - timedelta(days=i)).date()
        countedTickers = Counter(filteredTickers)
        countedTickers = dict(countedTickers)
        
        for key in countedTickers:
            if countedTickers[key] > MINREQMENTIONS:
                toAppend.append([d, key, countedTickers[key]])

        printProgressBar(i + 1, BACKDATE, prefix='Progress:', suffix='Complete', length=50)

    print("Successfully processed historical submissions. Generating plot.")
    dfMain = pd.DataFrame(toAppend, columns=["Date", "Ticker", "Count"])

    sns.lineplot(palette="tab10", data=dfMain, x="Date", y="Count", hue="Ticker", markers=True, style="Ticker", size="Ticker")
    plt.show()

def error(message):
    sys.exit("Error: " + message)

def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    if iteration == total: 
        print()

if __name__ == "__main__":
    TendieHunter()