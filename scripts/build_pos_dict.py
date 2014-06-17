#!/usr/bin/env python
import sys
import json
import nltk
from nltk.corpus import treebank

DISCARD_TAGS = ['-NONE-', 'CD']


def main():
    """
    Generate a list of most common words and parts of speech.
    """

    if len(sys.argv) < 3:
        print "USAGE: <NUM WORDS> <OUTPUT FILE>"
        sys.exit(1)

    num_words = int(sys.argv[1])
    output_path = sys.argv[2]

    # Retrieve the most frequent words and determine
    # their most common parts of speech
    print "Building the dictionary..."
    freq_dist = nltk.FreqDist(treebank.words())
    cond_freq_dist = nltk.ConditionalFreqDist(treebank.tagged_words())
    most_freq_words = freq_dist.keys()[:num_words]
    likely_tags = {
        word: cond_freq_dist[word].max()
        for word in most_freq_words
    }

    # Filter out parts of speech we don't need
    likely_tags = {
        word: tag for word, tag in likely_tags.iteritems()
        if tag not in DISCARD_TAGS
    }

    # Dump the data to a file
    with open(output_path, 'w') as output_file:
        output_str = json.dumps(likely_tags, indent=4)
        output_file.write(output_str)
    print u"Wrote output to {path}".format(path=output_path)


if __name__ == "__main__":
    main()
